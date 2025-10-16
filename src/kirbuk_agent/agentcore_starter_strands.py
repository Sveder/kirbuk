"""
Strands Agent sample with AgentCore
"""
import os
import json
import boto3
import sentry_sdk
from strands import Agent, tool
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from strands_tools.browser import AgentCoreBrowser

# Initialize Sentry
sentry_sdk.init(
    dsn="https://8478f940604801d031d8ae2952f13de2@o630775.ingest.us.sentry.io/4510198164094976",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

app = BedrockAgentCoreApp()

MEMORY_ID = os.getenv("BEDROCK_AGENTCORE_MEMORY_ID")
REGION = os.getenv("AWS_REGION")
MODEL_ID = "eu.anthropic.claude-sonnet-4-20250514-v1:0"
KIRBUK_BROWSER_IDENTIFIER = "kirbuk_browser_tool-l2a6PWdtMy"
S3_BUCKET = "sveder-kirbuk"
S3_STAGING_PREFIX = "staging_area"

ci_sessions = {}
current_session = None


def save_payload_to_s3(payload, submission_id):
    """Save the payload to S3 in the staging area"""
    try:
        s3_client = boto3.client('s3', region_name=REGION)

        # Create the S3 key: staging_area/<uuid>.json
        s3_key = f"{S3_STAGING_PREFIX}/{submission_id}.json"

        # Convert payload to JSON string
        json_data = json.dumps(payload, indent=2)

        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json_data,
            ContentType='application/json'
        )

        print(f"Successfully saved payload to s3://{S3_BUCKET}/{s3_key}")
        return s3_key

    except Exception as e:
        print(f"Error saving to S3: {e}")
        raise


@app.entrypoint
def invoke(payload, context):
    global current_session

    try:
        # Print all received data
        print("=" * 80)
        print("AGENT RECEIVED DATA")
        print("=" * 80)
        print(f"Full payload: {payload}")
        print("-" * 80)

        # Print each field individually
        if isinstance(payload, dict):
            for key, value in payload.items():
                # Mask password if present
                if 'password' in key.lower() and value:
                    print(f"{key}: ***")
                else:
                    print(f"{key}: {value}")

        print("-" * 80)
        print(f"Context: {context}")
        print("=" * 80)

        # Extract submission_id from payload
        submission_id = payload.get('submission_id') if isinstance(payload, dict) else None

        if submission_id:
            # Save payload to S3
            s3_key = save_payload_to_s3(payload, submission_id)
            print(f"Payload saved to S3: {s3_key}")
        else:
            print("Warning: No submission_id found in payload, skipping S3 save")

        if not MEMORY_ID:
            return {"error": "Memory not configured"}

        actor_id = context.headers.get('X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id', 'user') if hasattr(context, 'headers') else 'user'

        session_id = getattr(context, 'session_id', 'default')
        current_session = session_id
        print("OMG I'm here from server!")
        memory_config = AgentCoreMemoryConfig(
            memory_id=MEMORY_ID,
            session_id=session_id,
            actor_id=actor_id,
            retrieval_config={
                f"/users/{actor_id}/facts": RetrievalConfig(top_k=3, relevance_score=0.5),
                f"/users/{actor_id}/preferences": RetrievalConfig(top_k=3, relevance_score=0.5)
            }
        )

        browser_tool = AgentCoreBrowser(
            region=REGION,
            identifier=KIRBUK_BROWSER_IDENTIFIER
        )

        agent = Agent(
            model=MODEL_ID,
            session_manager=AgentCoreMemorySessionManager(memory_config, REGION),
            system_prompt="You are a helpful assistant. Use tools when appropriate.",
            tools=[browser_tool.browser]
        )

#        result = agent(payload.get("prompt", ""))

        browser_tool.close_platform()
        return {"response": "for now don't run anything just debugging"}
        return {"response": result.message.get('content', [{}])[0].get('text', str(result))}

    except Exception as e:
        # Capture exception in Sentry with context
        sentry_sdk.set_context("payload", payload)
        sentry_sdk.set_context("session", {
            "session_id": current_session,
            "actor_id": actor_id if 'actor_id' in locals() else 'unknown'
        })
        sentry_sdk.capture_exception(e)

        # Re-raise the exception to let the framework handle it
        raise

if __name__ == "__main__":
    app.run()
