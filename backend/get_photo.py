from common import table, respond, error, server_error, get_user_id, get_photo_id, to_api


def lambda_handler(event, context):
    try:
        photo_id = get_photo_id(event)
        if not photo_id:
            return error(400, "INVALID_ID", "photoId is not valid")
        item = table.get_item(Key={"userId": get_user_id(event), "photoId": photo_id}).get("Item")
        if not item:  # also covers "belongs to another user"
            return error(404, "NOT_FOUND", "Photo not found")
        return respond(200, to_api(item, with_original=True))
    except Exception:
        return server_error()
