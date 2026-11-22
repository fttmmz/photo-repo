
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

## Test Case 6: Small Load Test
- Test: Send multiple requests and measure response times.
- Expected Result: Requests complete without server errors.
- Status: Pending

