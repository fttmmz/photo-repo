from common import respond, server_error, get_user_id, to_api, all_user_photos


def lambda_handler(event, context):
    try:
        items = all_user_photos(get_user_id(event))
        return respond(200, {"items": [to_api(i) for i in items]})
    except Exception:
        return server_error()
