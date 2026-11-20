#!/usr/bin/env bash
set -euo pipefail
# Run from the repository root after the SAM stack has been deployed.
STACK="${1:-photo-repo}"
REGION="${AWS_REGION:-eu-north-1}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$ROOT/frontend/config.js"
if [[ ! -f "$CONFIG" ]]; then
  echo "Missing frontend/config.js. Copy config.example.js and fill in Cognito/API values first." >&2
  exit 1
fi
BUCKET="$(aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" --query "Stacks[0].Outputs[?OutputKey=='WebUiBucketName'].OutputValue" --output text)"
DIST="$(aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" --query "Stacks[0].Outputs[?OutputKey=='WebUiDistributionId'].OutputValue" --output text)"
if [[ -z "$BUCKET" || "$BUCKET" == "None" || -z "$DIST" || "$DIST" == "None" ]]; then
  echo "Could not find Member 2 CloudFormation outputs. Confirm the shared stack deployed successfully." >&2
  exit 1
fi
aws s3 sync "$ROOT/frontend/" "s3://$BUCKET/" --delete --exclude "config.example.js" --cache-control "public,max-age=300"
aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/*"
URL="$(aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" --query "Stacks[0].Outputs[?OutputKey=='WebUiUrl'].OutputValue" --output text)"
echo "Frontend uploaded. Open: $URL"
