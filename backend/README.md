# Member 3: Backend and API

Tasks (from the team plan):

- API Gateway routes: upload URL, list, get, delete, search
- API Lambda functions
- Error handling and request validation
- Throttling

Report sections: Compute and API section, API documentation.

## Files

| File | Lambda | IAM role (Member 5) |
| --- | --- | --- |
| `upload_url.py` | `UploadUrlFunction` | `UploadFunctionRole` |
| `list_photos.py` | `ListPhotosFunction` | `ListFunctionRole` |
| `get_photo.py` | `GetPhotoFunction` | `GetFunctionRole` |
| `search_photos.py` | `SearchPhotosFunction` | `SearchFunctionRole` |
| `delete_photo.py` | `DeletePhotoFunction` | `DeleteFunctionRole` |
| `common.py` | Shared helpers: responses, errors, user ID, presigned links | |
| `tests/test_api.py` | Unit tests (in-memory S3 and DynamoDB fakes) | |

All functions: Python 3.13, 256 MB, 10 s timeout, X-Ray tracing on. Settings are in the "Member 3" section of `template.yaml`.

## Running the tests

```bash
pip install boto3 pytest
pytest backend/tests
```

## API reference

Base URL: the `ApiUrl` stack output, for example `https://abc123.execute-api.eu-north-1.amazonaws.com/prod`.

Every request needs the Cognito **ID token** in the header `Authorization: <id token>`. Without a valid token, API Gateway returns `401` before any Lambda runs. The user is always taken from the token's `sub` claim, never from the request body or URL, so a user can only see and change their own photos.

### `POST /photos/upload-url` — start an upload

Request body (checked by API Gateway against the `UploadUrlRequest` model, then again in the Lambda):

| Field | Type | Rules |
| --- | --- | --- |
| `fileName` | string | Required, 1–200 characters |
| `contentType` | string | Required, `image/jpeg` or `image/png` |
| `fileSize` | integer | Required, bytes, 1 to 10,485,760 (10 MB) |
| `title` | string | Optional, up to 100 characters; defaults to `fileName` |
| `description` | string | Optional, up to 500 characters |
| `tags` | string array | Optional, up to 10 tags of 1–30 characters |

Response `201`:

```json
{
  "photoId": "6f1c...-uuid",
  "uploadUrl": "https://photo-repo-photos-...s3.amazonaws.com/",
  "fields": { "key": "originals/<sub>/<photoId>.jpg", "Content-Type": "image/jpeg", "...": "..." },
  "method": "POST",
  "expiresIn": 300
}
```

The browser then sends the file straight to S3 as `multipart/form-data`: every entry in `fields` first, then the file in a field named `file`. S3 itself rejects a different content type or a file over 10 MB. The photo record is saved as `PENDING` before the link is returned, and the resize function sets it to `READY` once the thumbnail exists.

### `GET /photos` — list my photos

Response `200`: `{"items": [Photo, ...]}`, newest first. Each item has a `thumbnailUrl` (valid 15 minutes), which is `null` while the photo is still `PENDING`.

### `GET /photos/{photoId}` — one photo at full size

Response `200`: a Photo with `mediumUrl` (up to 1280 px) and `originalUrl`, both valid 15 minutes. Returns `404` if the photo does not exist **or belongs to someone else**: the lookup uses the caller's own user ID, so other users' photos are never found.

### `GET /photos/search?q=<text>` — search my photos

`q` is 1–50 characters, case-insensitive. It matches part of the title (file name), one of the user's tags, or one of the Rekognition labels (when tagging is on). Response `200`: `{"query": "beach", "items": [Photo, ...]}`.

### `DELETE /photos/{photoId}` — delete a photo

Removes the original, the medium image, the thumbnail and the record. Response `200`: `{"photoId": "...", "deleted": true}`. A second request returns `404`. The buckets are versioned, so deleted files stay recoverable for 30 days.

### Photo object

```json
{
  "photoId": "6f1c...", "title": "Beach Day.jpg", "description": "",
  "tags": ["summer"], "labels": ["ocean"],
  "contentType": "image/jpeg", "size": 2400311, "width": 4032, "height": 3024,
  "status": "READY", "createdAt": "2026-11-21T18:00:00Z",
  "thumbnailUrl": "https://..."
}
```

`status` is `PENDING` (uploaded, not processed yet), `READY` or `FAILED` (the file could not be read as an image). `tags` are the user's own tags, and `labels` are Rekognition labels.

### Errors

All errors have the same shape: `{"error": {"code": "NOT_FOUND", "message": "Photo not found"}}`.

| Status | Code | When |
| --- | --- | --- |
| 400 | `INVALID_UPLOAD_REQUEST` | Upload body fails the API Gateway model (wrong type, too large, missing field) |
| 400 | `INVALID_JSON`, `UNSUPPORTED_TYPE`, `INVALID_SIZE`, `INVALID_TITLE`, `INVALID_DESCRIPTION`, `INVALID_TAGS` | The same checks repeated in the Lambda |
| 400 | `INVALID_ID` | `photoId` is not a UUID |
| 400 | `INVALID_QUERY` | `q` missing or longer than 50 characters |
| 401 | — | Missing, expired or invalid token (API Gateway) |
| 404 | `NOT_FOUND` | No such photo for this user |
| 413 | `FILE_TOO_LARGE` | `fileSize` over 10 MB (Lambda check) |
| 429 | — | Throttled (API Gateway) |
| 500 | `INTERNAL_ERROR` | Unexpected error; details go to CloudWatch Logs only |

Error responses from API Gateway itself (401, 429, 400 from the model) also carry CORS headers, so the browser can read them.

## Throttling

The `prod` stage allows a steady **20 requests per second** with bursts up to **40**, across all routes. Requests above that get `429 Too Many Requests` from API Gateway and never reach Lambda. The 30-user load test is expected to trigger this.

## Data contract with the resize function (Member 4)

| DynamoDB attribute | Written by | Notes |
| --- | --- | --- |
| `userId`, `photoId` | Upload | Partition and sort key |
| `title`, `titleLower`, `description`, `userTags`, `contentType`, `size`, `originalKey`, `createdAt` | Upload | `userTags` holds the user's tags |
| `status` | Upload (`PENDING`), resize (`READY` / `FAILED`) | |
| `thumbKey`, `mediumKey`, `width`, `height`, `tags`, `searchText`, `takenAt`, `processedAt` | Resize | `tags` holds Rekognition labels |

Original files are stored at `originals/<userId>/<photoId>.<jpg|png>` in the photo bucket. The resize function writes `thumb/<userId>/<photoId>.jpg` and `medium/<userId>/<photoId>.jpg` to the thumbnail bucket.

## Depends on

- Member 5's `UserPool` and the five `*FunctionRole` roles must be merged into `template.yaml` before this deploys.
- Member 2 reads `ApiUrl` from the stack outputs.
