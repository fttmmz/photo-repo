import importlib.util
import io
import os
from pathlib import Path

from botocore.exceptions import ClientError
from PIL import Image

os.environ.setdefault("TABLE_NAME", "test-table")
os.environ.setdefault("AWS_DEFAULT_REGION", "eu-north-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ["ENABLE_TAGGING"] = "false"

_path = Path(__file__).resolve().parents[1] / "resize" / "app.py"
_spec = importlib.util.spec_from_file_location("resize_app", _path)
resize_app = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(resize_app)

ORIGINALS, THUMBS = "originals-bucket", "thumbs-bucket"
USER, PHOTO = "user-1", "1731681234567-1a2b3c4d"
KEY = f"originals/{USER}/{PHOTO}.jpg"
ITEM = {"userId": USER, "photoId": PHOTO, "title": "Beach Day", "status": "PENDING"}


class FakeS3:
    def __init__(self, objects=None):
        self.objects = dict(objects or {})  # {(bucket, key): bytes}

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[(Bucket, Key)] = Body

    def delete_object(self, Bucket, Key):
        self.objects.pop((Bucket, Key), None)

    def delete_objects(self, Bucket, Delete):
        for obj in Delete["Objects"]:
            self.delete_object(Bucket, obj["Key"])


class FakeTable:
    def __init__(self, item, deleted_during_processing=False):
        self.item = item
        self.deleted_during_processing = deleted_during_processing
        self.updates = []

    def get_item(self, Key, **kwargs):
        return {"Item": dict(self.item)} if self.item else {}

    def update_item(self, **kwargs):
        if self.item is None or self.deleted_during_processing:
            raise ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException", "Message": "gone"}}, "UpdateItem"
            )
        self.updates.append(kwargs["ExpressionAttributeValues"])


def install(monkeypatch, objects=None, item=ITEM, **table_kwargs):
    s3, table = FakeS3(objects), FakeTable(item, **table_kwargs)
    monkeypatch.setattr(resize_app, "s3", s3)
    monkeypatch.setattr(resize_app, "table", table)
    monkeypatch.setattr(resize_app, "THUMB_BUCKET", THUMBS)
    return s3, table


def make_jpeg(width=800, height=600, orientation=None):
    kwargs = {}
    if orientation:
        exif = Image.Exif()
        exif[0x0112] = orientation
        kwargs["exif"] = exif
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (200, 80, 40)).save(buf, "JPEG", **kwargs)
    return buf.getvalue()


def open_image(s3, bucket, key):
    return Image.open(io.BytesIO(s3.objects[(bucket, key)]))


def test_makes_renditions_and_marks_ready(monkeypatch):
    s3, table = install(monkeypatch, {(ORIGINALS, KEY): make_jpeg()})
    resize_app.process(ORIGINALS, KEY)

    assert max(open_image(s3, THUMBS, f"thumb/{USER}/{PHOTO}.jpg").size) == 256
    assert open_image(s3, THUMBS, f"medium/{USER}/{PHOTO}.jpg").size == (800, 600)  # never enlarged
    assert (ORIGINALS, KEY) in s3.objects  # original untouched
    values = table.updates[-1]
    assert values[":st"] == "READY"
    assert (values[":w"], values[":h"]) == (800, 600)
    assert values[":tk"] == f"thumb/{USER}/{PHOTO}.jpg"
    assert values[":sx"] == "beach day"


def test_large_photo_is_capped_at_1280(monkeypatch):
    s3, table = install(monkeypatch, {(ORIGINALS, KEY): make_jpeg(4000, 3000)})
    resize_app.process(ORIGINALS, KEY)

    assert open_image(s3, THUMBS, f"medium/{USER}/{PHOTO}.jpg").size == (1280, 960)
    assert (table.updates[-1][":w"], table.updates[-1][":h"]) == (4000, 3000)


def test_phone_rotation_is_applied(monkeypatch):
    s3, table = install(monkeypatch, {(ORIGINALS, KEY): make_jpeg(600, 400, orientation=6)})
    resize_app.process(ORIGINALS, KEY)

    assert (table.updates[-1][":w"], table.updates[-1][":h"]) == (400, 600)


def test_transparent_png_gets_white_background(monkeypatch):
    buf = io.BytesIO()
    Image.new("RGBA", (100, 100), (255, 0, 0, 0)).save(buf, "PNG")
    key = f"originals/{USER}/{PHOTO}.png"
    s3, _ = install(monkeypatch, {(ORIGINALS, key): buf.getvalue()})
    resize_app.process(ORIGINALS, key)

    pixel = open_image(s3, THUMBS, f"medium/{USER}/{PHOTO}.jpg").getpixel((50, 50))
    assert all(channel >= 245 for channel in pixel)


def test_corrupt_file_is_marked_failed(monkeypatch):
    s3, table = install(monkeypatch, {(ORIGINALS, KEY): b"this is not an image"})
    resize_app.process(ORIGINALS, KEY)

    assert table.updates[-1][":st"] == "FAILED"
    assert not [k for k in s3.objects if k[0] == THUMBS]


def test_upload_without_metadata_is_removed(monkeypatch):
    s3, table = install(monkeypatch, {(ORIGINALS, KEY): make_jpeg()}, item=None)
    resize_app.process(ORIGINALS, KEY)

    assert s3.objects == {}
    assert table.updates == []


def test_folder_placeholders_and_other_paths_are_ignored(monkeypatch):
    s3, table = install(monkeypatch, {(ORIGINALS, KEY): make_jpeg()})
    for key in ("originals/", f"originals/{USER}/", "other/file.jpg", f"originals/{USER}/a/b.jpg"):
        resize_app.process(ORIGINALS, key)

    assert list(s3.objects) == [(ORIGINALS, KEY)]
    assert table.updates == []


def test_renditions_removed_if_photo_deleted_meanwhile(monkeypatch):
    s3, _ = install(monkeypatch, {(ORIGINALS, KEY): make_jpeg()}, deleted_during_processing=True)
    resize_app.process(ORIGINALS, KEY)

    assert not [k for k in s3.objects if k[0] == THUMBS]


def test_handler_skips_when_processing_disabled(monkeypatch):
    s3, table = install(monkeypatch, {(ORIGINALS, KEY): make_jpeg()})
    monkeypatch.setattr(resize_app, "PROCESS_UPLOADS", False)
    event = {"Records": [{"s3": {"bucket": {"name": ORIGINALS}, "object": {"key": KEY}}}]}
    resize_app.handler(event, None)

    assert table.updates == []
