
# Photo Repository – Test Cases

## Test Case 1: Upload Photo
- Test: Upload a photo to the website.
- Expected Result: Photo uploads successfully.
- Actual Result: Photo uploaded successfully.
- Status: Pass (Local Demo)

## Test Case 2: View Photos
- Test: View the uploaded photo.
- Expected Result: Photo is displayed.
- Actual Result: Photo appeared in Your Moments.
- Status: Pass (Local Demo)

## Test Case 3: Delete Photo
- Test: Delete an uploaded photo.
- Expected Result: Photo is deleted successfully.
- Actual Result: Photo disappeared after refreshing.
- Status: Pass (Local Demo)

## Test Case 4: File Size Validation
- Test: Upload an image larger than 10 MB.
- Expected Result: The website rejects the image.
- Actual Result: The website displayed a file size warning.
- Status: Pass (Local Demo)

## Test Case 5: AWS Backend
- Test: Retrieve photos using GET /photos.
- Expected Result: API returns photos successfully.
- Actual Result: Previous test returned HTTP 500.
- Status: Failed – Retest after backend updates.


## Test Case 6: Small Local HTTP Test

- Test: Send 10 sequential HTTP requests to the local website.
- Expected Result: All requests return HTTP 200.
- Actual Result: All 10 requests returned HTTP 200.
- Successful Requests: 10/10.
- Failed Requests: 0.
- Average Response Time: 0.001619 seconds.
- Status: Pass (Local Test).

Note: This test checks the local frontend server only.
AWS backend load testing is still pending.


