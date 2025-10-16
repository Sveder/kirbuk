"""
Strands Agent sample with AgentCore
"""
import os
from strands import Agent, tool
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from strands_tools.browser import AgentCoreBrowser


app = BedrockAgentCoreApp()

MEMORY_ID = os.getenv("BEDROCK_AGENTCORE_MEMORY_ID")
REGION = os.getenv("AWS_REGION")
MODEL_ID = "eu.anthropic.claude-sonnet-4-20250514-v1:0"
KIRBUK_BROWSER_IDENTIFIER = ""

ci_sessions = {}
current_session = None


@app.entrypoint
def invoke(payload, context):
    global current_session

    if not MEMORY_ID:
        return {"error": "Memory not configured"}

    actor_id = context.headers.get('X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id', 'user') if hasattr(context, 'headers') else 'user'

    session_id = getattr(context, 'session_id', 'default')
    current_session = session_id

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

    result = agent(payload.get("prompt", ""))
    
    browser_tool.close_platform()

    return {"response": result.message.get('content', [{}])[0].get('text', str(result))}

if __name__ == "__main__":
    app.run()
