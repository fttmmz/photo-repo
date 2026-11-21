from common import (respond, error, server_error, get_user_id, to_api, all_user_photos,
                    USER_TAGS_ATTR, LABELS_ATTR)


def matches(item, q):
    """True if q appears in the title, one of the user's tags or one of the Rekognition labels."""
    if q in item.get("titleLower", item.get("title", "").lower()):
        return True
    words = list(item.get(USER_TAGS_ATTR, [])) + list(item.get(LABELS_ATTR, []))
    return any(q in str(w).lower() for w in words)


def lambda_handler(event, context):
    try:
        qs = event.get("queryStringParameters") or {}
        q = (qs.get("q") or "").strip().lower()
        if not 1 <= len(q) <= 50:
            return error(400, "INVALID_QUERY", "q must be 1-50 characters")
        # Query reads only this user's partition; matching is done here so it can check
        # substrings inside tag lists, which a DynamoDB filter cannot do.
        items = [i for i in all_user_photos(get_user_id(event)) if matches(i, q)]
        return respond(200, {"query": q, "items": [to_api(i) for i in items]})
    except Exception:
        return server_error()
