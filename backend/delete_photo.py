from common import (s3, table, PHOTOS_BUCKET, THUMBS_BUCKET, respond, error,
                    server_error, get_user_id, get_photo_id)


def lambda_handler(event, context):
    try:
        photo_id = get_photo_id(event)
        if not photo_id:
            return error(400, "INVALID_ID", "photoId is not valid")
        key = {"userId": get_user_id(event), "photoId": photo_id}
        item = table.get_item(Key=key).get("Item")
        if not item:
            return error(404, "NOT_FOUND", "Photo not found")

        if item.get("originalKey"):
            s3.delete_object(Bucket=PHOTOS_BUCKET, Key=item["originalKey"])
        for attr in ("thumbnailKey", "mediumKey"):
            if item.get(attr):
                s3.delete_object(Bucket=THUMBS_BUCKET, Key=item[attr])
        table.delete_item(Key=key)
        return respond(200, {"photoId": photo_id, "deleted": True})
    except Exception:
        return server_error()
