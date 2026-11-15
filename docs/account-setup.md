# AWS account, team access and deployment setup (Member 1)

## Why not the AWS Academy sandbox

The Academy sandbox refused to create Amazon Cognito user pools and Amazon DynamoDB tables (`cognito-idp:CreateUserPool` and `dynamodb:CreateTable` were denied). Both are core to the design, so the project uses an AWS Free plan account instead.

## The account

- Created with **Sign up for AWS (new)** on the **Free plan**: usage comes out of free credits and is not charged to a card.
- The project is pinned to **Europe (Stockholm), `eu-north-1`**. Use this Region for everything (check it in AWS Settings, Project, Additional info).
- New accounts go through verification. Until it finishes, **CloudShell and new CloudFront distributions are blocked**; other services work. If CloudFront is still blocked when Member 2 needs it, open a free *Account and billing* support case and include the error message.

## Team access

- **AWS:** this account type gives team access through **collaborators** instead of IAM users. AWS Settings, your project, Collaborators, invite each member by email. Collaborators are administrators of the project, so invite only team members and agree not to delete shared resources without telling Member 1.
- **GitHub:** repository Settings, Collaborators, Add people. Each member accepts the email invite. Fill in real usernames in `.github/CODEOWNERS`.

## One-time laptop setup (because CloudShell is blocked)

Windows: install the **AWS CLI v2** (.msi from AWS), **Python** from python.org (tick *Add python.exe to PATH*) and **Git for Windows**; use **Git Bash**. Mac: install the AWS CLI v2 (.pkg) and Python; use Terminal.

```bash
aws --version              # 2.32 or higher, needed for "aws login"
aws login                  # browser sign-in; pick the project
aws configure set region eu-north-1
aws sts get-caller-identity
```

If a Python script later says `Missing Dependency ... botocore[crt]`: `python -m pip install --user "botocore[crt]"`.
If pip says `Can not combine '--user' and '--target'` (Microsoft Store Python): run `export PIP_USER=0` first.

## Deploy (after merging members' changes)

```bash
export AWS_REGION=eu-north-1
bash scripts/deploy.sh photo-repo
```

If it fails, get the reason, then delete the failed stack before trying again:

```bash
aws cloudformation describe-stack-events --stack-name photo-repo --query "StackEvents[?contains(ResourceStatus,'FAILED')].[LogicalResourceId,ResourceStatusReason]" --output text
aws cloudformation delete-stack --stack-name photo-repo
aws cloudformation wait stack-delete-complete --stack-name photo-repo
```
