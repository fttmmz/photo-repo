v # Member 6: Monitoring, testing and cost

Tasks (from the team plan):

- CloudWatch logs, metrics, dashboard
- Alarms (Lambda errors, API 5xx) with SNS alerts
- Test cases and a small load test
- Cost estimate and billing alarm

Report sections: Scalability/availability/monitoring, testing and results, cost analysis.

Put your code and notes in this folder, and your AWS resources in your section of `template.yaml`. Work on a branch and open a pull request.
## Work Completed

### 1. Amazon CloudWatch
- Created a CloudWatch dashboard to monitor the Photo Repository system.
- Added Lambda metrics: Errors, Invocations, and Duration.
- Added API Gateway metrics: 4XXError, 5XXError, and Latency.
- Configured CloudWatch alarms for monitoring errors.

### 2. Amazon SNS
- Created the SNS topic `PhotoRepository-Alerts`.
- Configured email notifications.
- Confirmed the email subscription.

### 3. AWS Budget
- Created `PhotoRepository-Monthly-Budget`.
- Set the monthly budget to $5.
- Configured budget alerts at 85% and 100%, including a forecasted cost alert.
- Verified the email recipient.

## Testing Status
- Initial GET /photos test returned HTTP 500 (Internal Server Error).
- Functional testing and a small load test are pending until backend integration is complete.

## Next Steps
- Complete functional testing and the small load test.
- Review CloudWatch logs and resolve any remaining errors with the backend team.
- Prepare the cost estimate and report documentation.
