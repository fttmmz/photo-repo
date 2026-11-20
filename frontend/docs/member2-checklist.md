# Member 2 handoff checklist

- [ ] Merge the Member 2 S3 bucket, CloudFront OAC, distribution and bucket policy into shared `template.yaml`.
- [ ] Add Member 2 CloudFormation outputs.
- [ ] Member 1 deploys the shared stack.
- [ ] Obtain Cognito User Pool ID and App Client ID from Member 5.
- [ ] Obtain API Gateway URL and confirm routes/JSON response fields with Member 3.
- [ ] Configure `frontend/config.js` (never commit it).
- [ ] Member 4 configures photo-bucket CORS for the CloudFront URL and presigned PUT headers.
- [ ] Deploy frontend using `scripts/deploy-frontend.sh photo-repo`.
- [ ] Test sign-up, confirmation, sign-in, upload, gallery, search, full-size view, delete and sign-out.
- [ ] Capture screenshots and CloudFront/S3 evidence for the report.
