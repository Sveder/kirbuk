"""
Simple test agent to explore Bedrock AgentCore environment
This agent will navigate to sveder.com and click the About button
to help us understand what files are created during execution.
"""
import os
import json
from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands_tools.browser import AgentCoreBrowser

app = BedrockAgentCoreApp()

# Environment variables that would be set by AgentCore
MEMORY_ID = os.getenv("BEDROCK_AGENTCORE_MEMORY_ID")
REGION = os.getenv("AWS_REGION", "eu-central-1")
MODEL_ID = "eu.anthropic.claude-sonnet-4-20250514-v1:0"
BROWSER_IDENTIFIER = "kirbuk_browser_tool-l2a6PWdtMy"  # Reusing the existing browser

@app.entrypoint
def invoke(payload, context):
    """
    Main entry point for the agent

    Args:
        payload: Input data (can be dict or other)
        context: Runtime context with session info
    """
    print("=" * 80)
    print("TEST AGENT STARTED")
    print("=" * 80)

    # Print environment info
    print("\nENVIRONMENT INFORMATION:")
    print(f"Working directory: {os.getcwd()}")
    print(f"MEMORY_ID: {MEMORY_ID}")
    print(f"REGION: {REGION}")
    print(f"MODEL_ID: {MODEL_ID}")

    # Print directory contents
    print("\nCURRENT DIRECTORY CONTENTS:")
    for item in os.listdir('.'):
        item_path = os.path.join('.', item)
        item_type = 'DIR' if os.path.isdir(item_path) else 'FILE'
        print(f"  [{item_type}] {item}")

    # Check /tmp directory
    print("\n/tmp DIRECTORY CONTENTS:")
    if os.path.exists('/tmp'):
        tmp_items = os.listdir('/tmp')
        print(f"  Found {len(tmp_items)} items in /tmp")
        for item in tmp_items[:20]:  # Show first 20 items
            print(f"    - {item}")
        if len(tmp_items) > 20:
            print(f"    ... and {len(tmp_items) - 20} more items")
    else:
        print("  /tmp does not exist")

    # Print payload and context info
    print("\nPAYLOAD:")
    print(json.dumps(payload if isinstance(payload, dict) else {"payload": str(payload)}, indent=2))

    print("\nCONTEXT:")
    print(f"  Session ID: {getattr(context, 'session_id', 'N/A')}")
    print(f"  Context attributes: {dir(context)}")

    # Initialize browser tool
    print("\n" + "=" * 80)
    print("INITIALIZING BROWSER TOOL")
    print("=" * 80)

    browser_tool = AgentCoreBrowser(
        region=REGION,
        identifier=BROWSER_IDENTIFIER
    )

    # Create agent with browser tool
    agent = Agent(
        model=MODEL_ID,
        system_prompt="""You are a test agent exploring a website.
Your task is simple:
1. Navigate to sveder.com
2. Find and click on the "About" button or link
3. Describe what you see

Be concise and just complete these steps.""",
        tools=[browser_tool.browser]
    )

    # Execute the task
    print("\n" + "=" * 80)
    print("EXECUTING BROWSER TASK")
    print("=" * 80)

    result = agent("Go to sveder.com and click on the About button")

    print("\n" + "=" * 80)
    print("TASK COMPLETED")
    print("=" * 80)

    # Close browser
    print("\nClosing browser...")
    browser_tool.close_platform()

    # Extract response
    response = result.message.get('content', [{}])[0].get('text', str(result))
    print(f"\nAgent response: {response}")

    # Check directory contents again after execution
    print("\n" + "=" * 80)
    print("POST-EXECUTION DIRECTORY SCAN")
    print("=" * 80)

    print("\nCURRENT DIRECTORY CONTENTS (after execution):")
    for item in os.listdir('.'):
        item_path = os.path.join('.', item)
        item_type = 'DIR' if os.path.isdir(item_path) else 'FILE'
        size = os.path.getsize(item_path) if os.path.isfile(item_path) else 'N/A'
        print(f"  [{item_type}] {item} (size: {size})")

    print("\n/tmp DIRECTORY CONTENTS (after execution):")
    if os.path.exists('/tmp'):
        tmp_items = os.listdir('/tmp')
        print(f"  Found {len(tmp_items)} items in /tmp")
        for item in sorted(tmp_items)[:30]:  # Show first 30 items
            item_path = os.path.join('/tmp', item)
            item_type = 'DIR' if os.path.isdir(item_path) else 'FILE'
            print(f"    [{item_type}] {item}")
        if len(tmp_items) > 30:
            print(f"    ... and {len(tmp_items) - 30} more items")

    # Look for common cache/temp directories
    print("\n" + "=" * 80)
    print("SEARCHING FOR COMMON CACHE/TEMP DIRECTORIES")
    print("=" * 80)

    common_dirs = [
        '/tmp',
        '/var/tmp',
        os.path.expanduser('~/.cache'),
        os.path.expanduser('~/.local'),
        '/tmp/playwright',
        '/tmp/browser',
        os.getcwd() + '/.cache',
    ]

    for dir_path in common_dirs:
        if os.path.exists(dir_path):
            try:
                items = os.listdir(dir_path)
                print(f"\n{dir_path}: {len(items)} items")
                for item in items[:10]:
                    print(f"  - {item}")
                if len(items) > 10:
                    print(f"  ... and {len(items) - 10} more items")
            except PermissionError:
                print(f"\n{dir_path}: Permission denied")
        else:
            print(f"\n{dir_path}: Does not exist")

    print("\n" + "=" * 80)
    print("TEST AGENT COMPLETED")
    print("=" * 80)

    return {"response": response, "test_completed": True}

if __name__ == "__main__":
    app.run()
