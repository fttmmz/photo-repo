#!/usr/bin/env bash
# Deploys (or updates) the shared stack from template.yaml using only the AWS CLI.
# Works in Git Bash (Windows), Terminal (Mac) or CloudShell. Member 1 runs it after merging changes.
#
# Usage:   bash scripts/deploy.sh [stack-name] [Key=Value ...]
#   bash scripts/deploy.sh photo-repo
#   bash scripts/deploy.sh photo-repo AlertEmail=team@example.com     # once a member adds that parameter
#
# Before running: aws login, and set the Region:  export AWS_REGION=eu-north-1
set -euo pipefail
export AWS_PAGER=""
cd "$(dirname "$0")/.."

STACK="${1:-photo-repo}"
shift || true
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-$(aws configure get region || true)}}"
if [ -z "$REGION" ]; then
  echo "No Region set. Run: export AWS_REGION=eu-north-1" >&2
  exit 1
fi
if ! [[ "$STACK" =~ ^[a-z0-9-]{1,15}$ ]]; then
  echo "Stack name must be lowercase letters, numbers and hyphens, 15 characters or fewer." >&2
  exit 1
fi

ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
ARTIFACTS="${STACK}-artifacts-${ACCOUNT}-${REGION}"
echo "Account $ACCOUNT, region $REGION, stack $STACK"

# Bucket that holds packaged Lambda code (created once)
if ! aws s3api head-bucket --bucket "$ARTIFACTS" 2>/dev/null; then
  echo "Creating artifact bucket $ARTIFACTS"
  if [ "$REGION" = "us-east-1" ]; then
    aws s3api create-bucket --bucket "$ARTIFACTS" --region "$REGION" > /dev/null
  else
    aws s3api create-bucket --bucket "$ARTIFACTS" --region "$REGION" \
      --create-bucket-configuration "LocationConstraint=$REGION" > /dev/null
  fi
fi

# Package any local Lambda code and deploy the stack
aws cloudformation package \
  --template-file template.yaml \
  --s3-bucket "$ARTIFACTS" \
  --output-template-file .packaged.yaml \
  --region "$REGION" > /dev/null

OVERRIDES=()
if [ "$#" -gt 0 ]; then
  OVERRIDES=(--parameter-overrides "$@")
fi

aws cloudformation deploy \
  --template-file .packaged.yaml \
  --stack-name "$STACK" \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
  --no-fail-on-empty-changeset \
  --region "$REGION" \
  ${OVERRIDES[@]+"${OVERRIDES[@]}"}

echo
aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
  --query "Stacks[0].[StackStatus, Outputs]" --output json
