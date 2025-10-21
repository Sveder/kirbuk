#!/bin/bash

# Script to recreate the Bedrock AgentCore Runtime IAM Role
# Role name: AmazonBedrockAgentCoreSDKRuntime-eu-central-1-9c0804ec0c
# Region: eu-central-1

ROLE_NAME="AmazonBedrockAgentCoreSDKRuntime-eu-central-1-9c0804ec0c"
REGION="eu-central-1"
POLICY_NAME="BedrockAgentCoreRuntimePolicy"

echo "Creating IAM role: $ROLE_NAME"

# Step 1: Create the IAM role with trust policy
aws iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document file://iam_role_trust_policy.json \
  --description "Execution role for Bedrock AgentCore runtime" \
  --tags Key=ManagedBy,Value=BedrockAgentCore Key=Region,Value=$REGION

echo "Role created successfully"

# Step 2: Attach the inline policy with permissions
aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "$POLICY_NAME" \
  --policy-document file://iam_role_permissions_policy.json

echo "Policy attached successfully"

# Step 3: Get the role ARN
ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)

echo ""
echo "============================================"
echo "IAM Role created successfully!"
echo "============================================"
echo "Role Name: $ROLE_NAME"
echo "Role ARN: $ROLE_ARN"
echo ""
echo "This role is now ready to use with Bedrock AgentCore"
