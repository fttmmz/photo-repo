import io
import logging
import os
import urllib.parse
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from PIL import Image, ImageOps

logger = logging.getLogger()
logger.setLevel(logging.INFO)

PROCESS_UPLOADS = os.environ.get("PROCESS_UPLOADS", "true") == "true"
ENABLE_TAGGING = os.environ.get("ENABLE_TAGGING", "false") == "true"
THUMB_BUCKET = os.environ.get("THUMB_BUCKET_NAME")  # unset -> renditions go to the source bucket

s3 = boto3.client("s3")
table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
rekognition = (
    boto3.client(
        "rekognition",
        config=Config(connect_timeout=3, read_timeout=10, retries={"max_attempts": 2}),
    )
    if ENABLE_TAGGING
    else None
)

RENDITIONS = (("medium", 1280), ("thumb", 256))  # largest first: each is made from the one before
Image.MAX_IMAGE_PIXELS = 50_000_000  # reject decompression bombs


def handler(event, context):
    if not PROCESS_UPLOADS:
        logger.info("Processing disabled; skipping %d records", len(event["Records"]))
        return
    for record in event["Records"]:
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        process(record["s3"]["bucket"]["name"], key)


def process(bucket, key):
    parts = key.split("/")
    photo_id = parts[-1].rsplit(".", 1)[0]
    if len(parts) != 3 or parts[0] != "originals" or not parts[1] or not photo_id:
        logger.info("Ignoring key %s", key)  # folder placeholders and unexpected paths
        return
    user_id = parts[1]
    item_key = {"userId": user_id, "photoId": photo_id}
    out_bucket = THUMB_BUCKET or bucket

    item = table.get_item(Key=item_key, ConsistentRead=True).get("Item")
    if not item:
        logger.warning("No metadata for %s; removing orphaned upload", key)
        s3.delete_object(Bucket=bucket, Key=key)
        return

    data = s3.get_object(Bucket=bucket, Key=key)["Body"].read()  # transient errors -> Lambda retries
    try:
        image, taken_at = _load(data)
    except Exception:
        logger.exception("Unreadable image %s", key)
        _set_status(item_key, "FAILED")
        return
    del data
    width, height = image.size  # original size, after applying phone rotation

    out_keys, medium_jpeg = {}, None
    for name, max_px in RENDITIONS:
        image.thumbnail((max_px, max_px), Image.Resampling.LANCZOS)  # in place; never enlarges
        buf = io.BytesIO()
        image.save(buf, "JPEG", quality=85, optimize=True, progressive=True)  # EXIF not copied -> GPS stripped
        out_keys[name] = f"{name}/{user_id}/{photo_id}.jpg"
        s3.put_object(Bucket=out_bucket, Key=out_keys[name], Body=buf.getvalue(), ContentType="image/jpeg")
        if name == "medium":
            medium_jpeg = buf.getvalue()

    tags = _labels(medium_jpeg) if ENABLE_TAGGING else []
    search_text = " ".join([item.get("title", ""), *tags]).strip().lower()

    try:
        table.update_item(
            Key=item_key,
            ConditionExpression="attribute_exists(photoId)",
            UpdateExpression="SET #st=:st, #w=:w, #h=:h, #tk=:tk, #mk=:mk, #tg=:tg, #sx=:sx, #ta=:ta, #pa=:pa",
            ExpressionAttributeNames={
                "#st": "status", "#w": "width", "#h": "height", "#tk": "thumbKey", "#mk": "mediumKey",
                "#tg": "tags", "#sx": "searchText", "#ta": "takenAt", "#pa": "processedAt",
            },
            ExpressionAttributeValues={
                ":st": "READY", ":w": width, ":h": height,
                ":tk": out_keys["thumb"], ":mk": out_keys["medium"], ":tg": tags,
                ":sx": search_text, ":ta": taken_at,
                ":pa": datetime.now(timezone.utc).isoformat(),
            },
        )
    except ClientError as err:
        if err.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        # Photo was deleted while processing: remove the renditions just created
        s3.delete_objects(Bucket=out_bucket, Delete={"Objects": [{"Key": k} for k in out_keys.values()]})


def _load(data):
    original = Image.open(io.BytesIO(data))
    taken_at = None
    try:
        exif = original.getexif()
        value = exif.get_ifd(0x8769).get(36867) or exif.get(306)  # DateTimeOriginal, then DateTime
        taken_at = str(value) if value else None
    except Exception:
        pass
    image = ImageOps.exif_transpose(original)  # respect phone rotation
    if image.mode in ("RGBA", "LA", "PA", "P"):
        rgba = image.convert("RGBA")
        image = Image.new("RGB", rgba.size, "white")
        image.paste(rgba, mask=rgba.getchannel("A"))
    elif image.mode != "RGB":
        image = image.convert("RGB")
    return image, taken_at


def _labels(jpeg_bytes):
    try:
        resp = rekognition.detect_labels(Image={"Bytes": jpeg_bytes}, MaxLabels=10, MinConfidence=80)
        return [label["Name"].lower() for label in resp["Labels"]]
    except (ClientError, BotoCoreError):
        logger.exception("Rekognition failed; continuing without tags")
        return []


def _set_status(item_key, status):
    try:
        table.update_item(
            Key=item_key,
            ConditionExpression="attribute_exists(photoId)",
            UpdateExpression="SET #st = :st",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={":st": status},
        )
    except ClientError as err:
        if err.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
