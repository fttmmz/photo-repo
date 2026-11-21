import json, os, re, traceback
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config

REGION = os.environ["AWS_REGION"]  # set automatically by Lambda
PHOTOS_BUCKET = os.environ["PHOTOS_BUCKET"]
THUMBS_BUCKET = os.environ["THUMBS_BUCKET"]
TABLE_NAME = os.environ["TABLE_NAME"]
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")
KEY_PREFIX = "originals/"  # the resize function is triggered by this prefix
UPLOAD_URL_TTL = 300       # seconds
VIEW_URL_TTL = 900         # seconds (15 minutes, as stated in the report)
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

s3 = boto3.client("s3", region_name=REGION,
                  config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}))
table = boto3.resource("dynamodb").Table(TABLE_NAME)


def _json_default(o):
    if isinstance(o, Decimal):
        return int(o) if o % 1 == 0 else float(o)
    if isinstance(o, set):
        return list(o)
    raise TypeError(f"Not serializable: {type(o)}")


def respond(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
        },
        "body": json.dumps(body, default=_json_default),
    }


def error(status, code, message):
    return respond(status, {"error": {"code": code, "message": message}})


def server_error():
    traceback.print_exc()  # shows up in CloudWatch Logs
    return error(500, "INTERNAL_ERROR", "Something went wrong. Please try again.")


def get_user_id(event):
    return event["requestContext"]["authorizer"]["claims"]["sub"]


def get_photo_id(event):
    photo_id = (event.get("pathParameters") or {}).get("photoId", "")
    return photo_id if UUID_RE.match(photo_id) else None


def presign_get(bucket, key):
    if not key:
        return None
    return s3.generate_presigned_url("get_object",
                                     Params={"Bucket": bucket, "Key": key},
                                     ExpiresIn=VIEW_URL_TTL)


# DynamoDB attribute names shared with the resize function (storage-processing/resize/app.py).
# The resize function writes thumbKey, mediumKey and tags (Rekognition labels), so the
# user's own tags are kept in userTags to stop the resize step overwriting them.
THUMB_KEY_ATTR = "thumbKey"
MEDIUM_KEY_ATTR = "mediumKey"
USER_TAGS_ATTR = "userTags"
LABELS_ATTR = "tags"


def to_api(item, with_original=False):
    """Shape a DynamoDB item for the API.

    List and search (with_original=False) return a thumbnail link; their roles can read thumb/*.
    Get (with_original=True) returns medium and original links; its role can read medium/* and
    originals/* but not thumb/*, so no thumbnail link is signed there.
    """
    photo = {
        "photoId": item["photoId"],
        "title": item.get("title", ""),
        "description": item.get("description", ""),
        "tags": item.get(USER_TAGS_ATTR, []),
        "labels": item.get(LABELS_ATTR, []),
        "contentType": item.get("contentType"),
        "size": item.get("size"),
        "width": item.get("width"),
        "height": item.get("height"),
        "status": item.get("status", "PENDING"),
        "createdAt": item.get("createdAt"),
    }
    if with_original:
        photo["mediumUrl"] = presign_get(THUMBS_BUCKET, item.get(MEDIUM_KEY_ATTR))
        photo["originalUrl"] = presign_get(PHOTOS_BUCKET, item.get("originalKey"))
    else:
        photo["thumbnailUrl"] = presign_get(THUMBS_BUCKET, item.get(THUMB_KEY_ATTR))
    return photo


def all_user_photos(user_id):
    """Get every photo for one user, newest first. Only that user's partition is read."""
    params = {"KeyConditionExpression": Key("userId").eq(user_id)}
    items = []
    while True:
        res = table.query(**params)
        items.extend(res["Items"])
        if "LastEvaluatedKey" not in res:
            break
        params["ExclusiveStartKey"] = res["LastEvaluatedKey"]
    items.sort(key=lambda i: i.get("createdAt", ""), reverse=True)
    return items
