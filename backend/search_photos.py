from boto3.dynamodb.conditions import Attr
from common import respond, error, server_error, get_user_id, to_api, all_user_photos


def lambda_handler(event, context):
    try:
        qs = event.get("queryStringParameters") or {}
        q = (qs.get("q") or "").strip().lower()
        if not 1 <= len(q) <= 50:
            return error(400, "INVALID_QUERY", "q must be 1-50 characters")
        match = (Attr("titleLower").contains(q)
                 | Attr("tags").contains(q)
                 | Attr("labels").contains(q))
        items = all_user_photos(get_user_id(event), match)
        return respond(200, {"query": q, "items": [to_api(i) for i in items]})
    except Exception:
        return server_error()
