"""Unit tests for the API Lambda functions.

They replace S3 and DynamoDB with small in-memory fakes, so they run without an AWS account:
    pip install boto3 pytest
    pytest backend/tests
"""
import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("AWS_REGION", "eu-north-1")
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-north-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("PHOTOS_BUCKET", "photos-bucket")
os.environ.setdefault("THUMBS_BUCKET", "thumbs-bucket")
os.environ.setdefault("TABLE_NAME", "test-table")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import common  # noqa: E402
import delete_photo  # noqa: E402
import get_photo  # noqa: E402
import list_photos  # noqa: E402
import search_photos  # noqa: E402
import upload_url  # noqa: E402

PHOTOS, THUMBS = "photos-bucket", "thumbs-bucket"
ALICE, BOB = "alice-sub", "bob-sub"
P1 = "11111111-1111-4111-8111-111111111111"
P2 = "22222222-2222-4222-8222-222222222222"
P3 = "33333333-3333-4333-8333-333333333333"


class ConditionalCheckFailed(Exception):
    pass


class FakeS3:
    def __init__(self):
        self.deleted = []

    def generate_presigned_url(self, op, Params, ExpiresIn):
        return f"https://{Params['Bucket']}/{Params['Key']}?expires={ExpiresIn}"

    def generate_presigned_post(self, Bucket, Key, Fields, Conditions, ExpiresIn):
        return {"url": f"https://{Bucket}", "fields": {**Fields, "key": Key},
                "conditions": Conditions, "expires": ExpiresIn}

    def delete_object(self, Bucket, Key):
        self.deleted.append((Bucket, Key))


class FakeTable:
    def __init__(self, items=()):
        self.items = {(i["userId"], i["photoId"]): dict(i) for i in items}

    def get_item(self, Key, **kwargs):
        item = self.items.get((Key["userId"], Key["photoId"]))
        return {"Item": dict(item)} if item else {}

    def put_item(self, Item, ConditionExpression=None):
        k = (Item["userId"], Item["photoId"])
        if ConditionExpression and k in self.items:
            raise ConditionalCheckFailed()
        self.items[k] = dict(Item)

    def delete_item(self, Key):
        self.items.pop((Key["userId"], Key["photoId"]), None)

    def query(self, KeyConditionExpression, **kwargs):
        user_id = KeyConditionExpression.get_expression()["values"][1]
        return {"Items": [dict(v) for (u, _), v in self.items.items() if u == user_id]}


def ready(user, photo_id, title, created, user_tags=(), labels=()):
    """A record as it looks after the resize function has processed the upload."""
    return {
        "userId": user, "photoId": photo_id, "title": title, "titleLower": title.lower(),
        "userTags": list(user_tags), "tags": list(labels), "status": "READY", "createdAt": created,
        "originalKey": f"originals/{user}/{photo_id}.jpg",
        "thumbKey": f"thumb/{user}/{photo_id}.jpg", "mediumKey": f"medium/{user}/{photo_id}.jpg",
    }


@pytest.fixture
def aws(monkeypatch):
    s3, table = FakeS3(), FakeTable([
        ready(ALICE, P1, "Beach Day", "2026-11-01T10:00:00Z", user_tags=["summer"], labels=["ocean"]),
        ready(ALICE, P2, "Graduation", "2026-11-02T10:00:00Z"),
        ready(BOB, P3, "Bob Beach", "2026-11-03T10:00:00Z"),
    ])
    for module in (common, upload_url, list_photos, get_photo, search_photos, delete_photo):
        if hasattr(module, "s3"):
            monkeypatch.setattr(module, "s3", s3)
        if hasattr(module, "table"):
            monkeypatch.setattr(module, "table", table)
    return s3, table


def event(user, body=None, photo_id=None, query=None):
    return {
        "requestContext": {"authorizer": {"claims": {"sub": user}}},
        "body": body if body is None or isinstance(body, str) else json.dumps(body),
        "pathParameters": {"photoId": photo_id} if photo_id else None,
        "queryStringParameters": query,
    }


def call(module, evt):
    res = module.lambda_handler(evt, None)
    assert res["headers"]["Access-Control-Allow-Origin"]  # every response carries CORS headers
    return res["statusCode"], json.loads(res["body"])


# ---------- Upload (FR2) ----------

def test_upload_creates_pending_record_and_limited_presigned_post(aws):
    s3, table = aws
    status, body = call(upload_url, event(ALICE, {
        "fileName": "Cat.PNG", "contentType": "image/png", "fileSize": 2048, "tags": ["Pets", "pets"],
        "userId": BOB,  # must be ignored: the owner comes only from the token
    }))
    assert status == 201
    item = table.items[(ALICE, body["photoId"])]
    assert item["status"] == "PENDING"
    assert item["originalKey"] == f"originals/{ALICE}/{body['photoId']}.png"
    assert item["userTags"] == ["pets"] and "tags" not in item
    assert item["titleLower"] == "cat.png"
    assert body["fields"]["Content-Type"] == "image/png"
    assert body["fields"]["key"] == item["originalKey"]


def test_upload_presigned_post_enforces_size_and_type(aws, monkeypatch):
    seen = {}
    original = aws[0].generate_presigned_post

    def spy(**kwargs):
        seen.update(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(aws[0], "generate_presigned_post", spy)
    call(upload_url, event(ALICE, {"fileName": "a.jpg", "contentType": "image/jpeg", "fileSize": 10}))
    assert ["content-length-range", 1, 10 * 1024 * 1024] in seen["Conditions"]
    assert {"Content-Type": "image/jpeg"} in seen["Conditions"]
    assert seen["ExpiresIn"] == common.UPLOAD_URL_TTL


@pytest.mark.parametrize("body, status, code", [
    ({"fileName": "a.gif", "contentType": "image/gif", "fileSize": 10}, 400, "UNSUPPORTED_TYPE"),
    ({"fileName": "a.jpg", "contentType": "image/jpeg", "fileSize": 11 * 1024 * 1024}, 413, "FILE_TOO_LARGE"),
    ({"fileName": "a.jpg", "contentType": "image/jpeg", "fileSize": "10"}, 400, "INVALID_SIZE"),
    ("{not json", 400, "INVALID_JSON"),
])
def test_upload_rejects_bad_requests(aws, body, status, code):
    got_status, got = call(upload_url, event(ALICE, body))
    assert (got_status, got["error"]["code"]) == (status, code)
    assert len(aws[1].items) == 3  # nothing written


# ---------- List (FR3) ----------

def test_list_returns_only_own_photos_newest_first_with_thumbnail_links(aws):
    status, body = call(list_photos, event(ALICE))
    assert status == 200
    assert [p["photoId"] for p in body["items"]] == [P2, P1]
    assert body["items"][1]["thumbnailUrl"] == f"https://{THUMBS}/thumb/{ALICE}/{P1}.jpg?expires=900"
    assert "originalUrl" not in body["items"][0]


def test_list_shows_pending_photo_without_thumbnail(aws):
    aws[1].put_item({"userId": ALICE, "photoId": P3, "title": "new", "status": "PENDING",
                     "createdAt": "2026-11-05T00:00:00Z"})
    _, body = call(list_photos, event(ALICE))
    assert body["items"][0]["status"] == "PENDING" and body["items"][0]["thumbnailUrl"] is None


def test_user_tags_survive_resize_and_labels_are_separate(aws):
    _, body = call(list_photos, event(ALICE))
    beach = next(p for p in body["items"] if p["photoId"] == P1)
    assert beach["tags"] == ["summer"] and beach["labels"] == ["ocean"]


# ---------- Get (FR4, NFR1) ----------

def test_get_returns_15_minute_medium_and_original_links(aws):
    status, body = call(get_photo, event(ALICE, photo_id=P1))
    assert status == 200
    assert body["originalUrl"] == f"https://{PHOTOS}/originals/{ALICE}/{P1}.jpg?expires=900"
    assert body["mediumUrl"] == f"https://{THUMBS}/medium/{ALICE}/{P1}.jpg?expires=900"
    assert "thumbnailUrl" not in body  # the Get role cannot read thumb/*


def test_get_another_users_photo_is_not_found(aws):
    status, body = call(get_photo, event(BOB, photo_id=P1))
    assert (status, body["error"]["code"]) == (404, "NOT_FOUND")


def test_get_rejects_malformed_id(aws):
    status, body = call(get_photo, event(ALICE, photo_id="../../etc"))
    assert (status, body["error"]["code"]) == (400, "INVALID_ID")


# ---------- Search (FR6) ----------

@pytest.mark.parametrize("q, expected", [
    ("beach", [P1]),       # file name / title, and never Bob's "Bob Beach"
    ("SUMMER", [P1]),      # user tag, case-insensitive
    ("ocean", [P1]),       # Rekognition label
    ("grad", [P2]),        # partial title
    ("nothing", []),
])
def test_search_matches_title_tags_and_labels_for_own_photos(aws, q, expected):
    status, body = call(search_photos, event(ALICE, query={"q": q}))
    assert status == 200
    assert [p["photoId"] for p in body["items"]] == expected


def test_search_requires_query(aws):
    status, body = call(search_photos, event(ALICE, query=None))
    assert (status, body["error"]["code"]) == (400, "INVALID_QUERY")


# ---------- Delete (FR5) ----------

def test_delete_removes_original_renditions_and_record_then_404(aws):
    s3, table = aws
    status, _ = call(delete_photo, event(ALICE, photo_id=P1))
    assert status == 200
    assert (ALICE, P1) not in table.items
    assert set(s3.deleted) == {
        (PHOTOS, f"originals/{ALICE}/{P1}.jpg"),
        (THUMBS, f"thumb/{ALICE}/{P1}.jpg"),
        (THUMBS, f"medium/{ALICE}/{P1}.jpg"),
    }
    status, body = call(delete_photo, event(ALICE, photo_id=P1))
    assert (status, body["error"]["code"]) == (404, "NOT_FOUND")


def test_delete_pending_photo_still_clears_rendition_paths(aws):
    s3, table = aws
    table.put_item({"userId": ALICE, "photoId": P3, "status": "PENDING",
                    "originalKey": f"originals/{ALICE}/{P3}.png"})
    call(delete_photo, event(ALICE, photo_id=P3))
    assert (THUMBS, f"thumb/{ALICE}/{P3}.jpg") in s3.deleted
    assert (THUMBS, f"medium/{ALICE}/{P3}.jpg") in s3.deleted


def test_delete_another_users_photo_is_not_found_and_touches_nothing(aws):
    s3, table = aws
    status, _ = call(delete_photo, event(BOB, photo_id=P1))
    assert status == 404 and s3.deleted == [] and (ALICE, P1) in table.items


# ---------- Errors ----------

def test_unexpected_error_returns_generic_500(aws, monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(aws[1], "query", boom)
    status, body = call(list_photos, event(ALICE))
    assert status == 500 and "secret" not in json.dumps(body)
