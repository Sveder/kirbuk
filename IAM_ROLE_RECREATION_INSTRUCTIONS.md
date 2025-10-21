# IAM Role Restoration Instructions

## Problem
The IAM role `AmazonBedrockAgentCoreSDKRuntime-eu-central-1-9c0804ec0c` was deleted when the test agent was destroyed. This role is required for the kirbuk_agent to run.

## Solution
Recreate the IAM role with the same name and permissions.

## Files Created
1. `iam_role_trust_policy.json` - Trust policy allowing bedrock-agentcore.amazonaws.com to assume the role
2. `iam_role_permissions_policy.json` - Inline policy with necessary permissions
3. `create_iam_role_commands.sh` - Executable script to create the role

## Permissions Included
- **Bedrock**: InvokeModel, InvokeModelWithResponseStream
- **S3**: GetObject, PutObject, ListBucket (for sveder-kirbuk bucket)
- **Polly**: SynthesizeSpeech (for voice generation)
- **Bedrock AgentCore Memory**: Full memory operations
- **CloudWatch Logs**: CreateLogGroup, CreateLogStream, PutLogEvents
- **X-Ray**: PutTraceSegments, PutTelemetryRecords (for observability)

## To Create the Role

### Option 1: Run the script
```bash
cd /home/ubuntu/kirbuk
./create_iam_role_commands.sh
```

### Option 2: Manual commands
```bash
# Create role
aws iam create-role \
  --role-name AmazonBedrockAgentCoreSDKRuntime-eu-central-1-9c0804ec0c \
  --assume-role-policy-document file://iam_role_trust_policy.json \
  --description "Execution role for Bedrock AgentCore runtime"

# Attach policy
aws iam put-role-policy \
  --role-name AmazonBedrockAgentCoreSDKRuntime-eu-central-1-9c0804ec0c \
  --policy-name BedrockAgentCoreRuntimePolicy \
  --policy-document file://iam_role_permissions_policy.json
```

## Expected Output
```
Role ARN: arn:aws:iam::800622328366:role/AmazonBedrockAgentCoreSDKRuntime-eu-central-1-9c0804ec0c
```

## Verification
After creation, verify the role exists:
```bash
aws iam get-role --role-name AmazonBedrockAgentCoreSDKRuntime-eu-central-1-9c0804ec0c
```

## Note
The kirbuk_agent configuration already references this role ARN, so once created, the agent should work without any code changes.
