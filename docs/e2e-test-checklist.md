# End-to-end test plan (Member 1: final integration and end-to-end testing)

Run after every member's part is merged and deployed. Record a screenshot or log line per row as evidence. Member 6 can reuse the results in the Testing and Results section.

| ID | Scenario | Expected result | Covers |
| --- | --- | --- | --- |
| E2E-1 | Register, confirm and sign in | Gallery page loads; a wrong password is refused | FR1 |
| E2E-2 | Upload a JPEG | Original appears in S3, a record appears in DynamoDB, a thumbnail follows shortly after | FR2, FR7 |
| E2E-3 | Open the gallery | Only the signed-in user's thumbnails are listed | FR3 |
| E2E-4 | Open a photo at full size | The image loads through a time-limited link | FR4 |
| E2E-5 | Search by file name | Only matching photos are returned | FR6 |
| E2E-6 | Delete a photo | Original, thumbnail and record are gone; a repeat request returns not found | FR5 |
| E2E-7 | Call the API with no login token | 401 Unauthorized | NFR1 |
| E2E-8 | Sign in as user B and request user A's photo | Access refused | NFR1 |
| E2E-9 | Open a photo's bare S3 address | AccessDenied | NFR1 |
| E2E-10 | Upload an unsupported or oversized file | Rejected with a clear error | FR2 |
| E2E-11 | Force a Lambda error | CloudWatch alarm fires and an SNS email arrives | NFR5 |

Results: to be filled in after the final deployment.
