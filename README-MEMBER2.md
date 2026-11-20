# Cloud Frame — Member 2 Frontend and Content Delivery

This folder contains the frontend implementation for the Serverless Photo Repository.

## Included
- Cognito sign-up, email confirmation, sign-in, sign-out and session restoration.
- Responsive photo gallery, upload (JPEG/PNG, 10 MB proposed limit), full-size viewer, delete and filename/tag search.
- Browser-to-S3 upload using the presigned URL returned by the backend API.
- Private S3 static website origin, CloudFront Origin Access Control and HTTPS distribution (template snippet).
- Deployment helper that syncs the frontend to S3 and invalidates CloudFront.

## Important integration dependencies
This is the Member 2 implementation, not a claim that the complete AWS application is already deployed. It needs:
1. Member 5's Cognito User Pool ID and App Client ID.
2. Member 3's API Gateway base URL and API response contract.
3. Member 4's photo bucket CORS rule permitting browser PUT from the CloudFront website origin, and allowing the Content-Type header.
4. Member 1 to merge the resource snippets into the shared `template.yaml`, deploy the stack and provide the outputs.

## Preview before AWS integration
From the `frontend/` folder, run `python3 -m http.server 8000`, open `http://localhost:8000`, and choose **Preview website with demo photos**. This lets you inspect the gallery, search, image viewer, local demo uploads and delete interaction without Cognito or API Gateway. Demo changes are temporary and do not upload to AWS. This preview is not evidence of live authentication or cloud storage.

## Configure
From the repository root:
```bash
cp frontend/config.example.js frontend/config.js
```
Edit `frontend/config.js` with the actual values from Members 3 and 5. Do not commit `config.js` or credentials.

## Confirmed team API contract
API base URL: `https://vxmczuhddl.execute-api.eu-north-1.amazonaws.com/prod` (region `eu-north-1`). All API calls except the presigned S3 PUT carry `Authorization: <Cognito ID token>` with no `Bearer` prefix.

| Operation | Request | Expected response |
|---|---|---|
| Create upload URL | `POST /photos/upload-url` JSON `{fileName, contentType, fileSize, title, tags}` | `{photoId, uploadUrl}` |
| Upload file | `PUT <uploadUrl>` with original file and `Content-Type` header; no Authorization header | S3 success response |
| List | `GET /photos` | `{items:[photo, ...]}` (newest first) |
| Search | `GET /photos/search?q=cat` | `{query, items:[photo, ...]}` |
| Get full image URL | `GET /photos/{photoId}` | photo object including `originalUrl` |
| Delete | `DELETE /photos/{photoId}` | `{photoId, deleted:true}` |

Photo objects include `photoId`, `title`, `description`, `tags`, `labels`, `contentType`, `size`, `status`, `createdAt`, and `thumbnailUrl` (which may be null until processing completes). `originalUrl` is returned by the individual-photo GET endpoint. The frontend search treats the query literally and case-insensitively, so parentheses and digits in filenames such as `Image(2).jpg` and `Image(3).jpg` are preserved.

The upload request's `fileSize` field is the exact field name supplied by Member 3. The original bucket key format supplied by Member 4 is `originals/{userId}/{photoId}.{extension}`; the backend generates/uses this key. The frontend does not need direct DynamoDB access.

## AWS hosting deployment
The current shared `template.yaml` already includes the Member 2 private website bucket and CloudFront resources. The Member 3, 4, and 5 sections are still integration placeholders in this repository snapshot. Member 1 should merge those members' actual resources and deploy the shared SAM stack using the team's normal process.

Then configure and deploy:
```bash
cp frontend/config.example.js frontend/config.js
# edit frontend/config.js with the real Cognito/API values
AWS_REGION=eu-north-1 bash scripts/deploy-frontend.sh photo-repo
```
The script requires AWS CLI credentials and permissions for CloudFormation read, S3 sync and CloudFront invalidation.

## Important CORS requirement
The photo S3 bucket is separate from the private website bucket. Member 4 confirmed the original bucket currently allows GET and POST. Because the backend returns a presigned URL that the browser uploads to using PUT, the original photo bucket must also allow `PUT` from the exact website origin and allow the `Content-Type` header. The thumbnail bucket needs `GET` CORS only if the browser loads thumbnails directly from that bucket; confirm whether thumbnails are served directly or through another URL. Do not make either photo bucket public.

## Notes
- The CloudFront distribution uses the default CloudFront certificate and redirects HTTP to HTTPS.
- The web UI bucket is private; CloudFront reads it using OAC. S3 website hosting/public access is intentionally not enabled.
- The Cognito JavaScript SDK is loaded from a CDN. For a fully offline/self-contained build, vendor the SDK into `frontend/assets/` and update the script reference.
- The 10 MB maximum is a client-side guard only. Member 3 must validate upload size/type server-side as well.
