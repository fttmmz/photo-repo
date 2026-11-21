import json, uuid
from datetime import datetime, timezone
from common import (s3, table, PHOTOS_BUCKET, KEY_PREFIX, UPLOAD_URL_TTL, USER_TAGS_ATTR,
                    respond, error, server_error, get_user_id)

ALLOWED_TYPES = {"image/jpeg": "jpg", "image/png": "png"}
MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def clean_tags(raw):
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > 10:
        raise ValueError("tags must be a list of at most 10 strings")
    tags = set()
    for t in raw:
        if not isinstance(t, str) or not t.strip() or len(t.strip()) > 30:
            raise ValueError("each tag must be 1-30 characters")
        tags.add(t.strip().lower())
    return sorted(tags)


def lambda_handler(event, context):
    try:
        try:
            body = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return error(400, "INVALID_JSON", "Request body must be valid JSON")

        content_type = body.get("contentType")
        size = body.get("fileSize")
        file_name = str(body.get("fileName") or "").strip()
        title = str(body.get("title") or file_name).strip()
        description = str(body.get("description") or "").strip()

        if content_type not in ALLOWED_TYPES:
            return error(400, "UNSUPPORTED_TYPE", "Only JPEG and PNG images are allowed")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            return error(400, "INVALID_SIZE", "fileSize must be a positive integer (bytes)")
        if size > MAX_BYTES:
            return error(413, "FILE_TOO_LARGE", "Maximum file size is 10 MB")
        if not title or len(title) > 100:
            return error(400, "INVALID_TITLE", "title (or fileName) must be 1-100 characters")
        if len(description) > 500:
            return error(400, "INVALID_DESCRIPTION", "description must be at most 500 characters")
        try:
            tags = clean_tags(body.get("tags"))
        except ValueError as e:
            return error(400, "INVALID_TAGS", str(e))

        user_id = get_user_id(event)
        photo_id = str(uuid.uuid4())
        key = f"{KEY_PREFIX}{user_id}/{photo_id}.{ALLOWED_TYPES[content_type]}"
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # The record is written before the upload link is handed out, so the resize
        # function always finds it. User tags go in userTags: the resize step writes "tags".
        table.put_item(
            Item={
                "userId": user_id, "photoId": photo_id,
                "title": title, "titleLower": title.lower(), "description": description,
                USER_TAGS_ATTR: tags, "contentType": content_type, "size": size,
                "originalKey": key, "status": "PENDING", "createdAt": now,
            },
            ConditionExpression="attribute_not_exists(photoId)",
        )

        # Presigned POST: S3 itself enforces the content type and the 10 MB limit
        post = s3.generate_presigned_post(
            Bucket=PHOTOS_BUCKET,
            Key=key,
            Fields={"Content-Type": content_type},
            Conditions=[{"Content-Type": content_type},
                        ["content-length-range", 1, MAX_BYTES]],
            ExpiresIn=UPLOAD_URL_TTL,
        )
        return respond(201, {
            "photoId": photo_id,
            "uploadUrl": post["url"],
            "fields": post["fields"],
            "method": "POST",
            "expiresIn": UPLOAD_URL_TTL,
        })
    except Exception:
        return server_error()
