from common import (s3, table, PHOTOS_BUCKET, THUMBS_BUCKET, THUMB_KEY_ATTR, MEDIUM_KEY_ATTR,
                    respond, error, server_error, get_user_id, get_photo_id)


def lambda_handler(event, context):
    try:
        photo_id = get_photo_id(event)
        if not photo_id:
            return error(400, "INVALID_ID", "photoId is not valid")
        user_id = get_user_id(event)
        key = {"userId": user_id, "photoId": photo_id}
        item = table.get_item(Key=key, ConsistentRead=True).get("Item")
        if not item:  # also covers "belongs to another user"
            return error(404, "NOT_FOUND", "Photo not found")

        if item.get("originalKey"):
            s3.delete_object(Bucket=PHOTOS_BUCKET, Key=item["originalKey"])
        # Fall back to the resize function's fixed paths, so renditions written just after
        # we read a PENDING record are still removed.
        rendition_keys = {
            item.get(THUMB_KEY_ATTR) or f"thumb/{user_id}/{photo_id}.jpg",
            item.get(MEDIUM_KEY_ATTR) or f"medium/{user_id}/{photo_id}.jpg",
        }
        for k in sorted(rendition_keys):
            s3.delete_object(Bucket=THUMBS_BUCKET, Key=k)
        table.delete_item(Key=key)
        return respond(200, {"photoId": photo_id, "deleted": True})
    except Exception:
        return server_error()
