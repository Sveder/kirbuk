"""
Simple test runner that directly calls the test agent
"""
import os
import sys

# Set required environment variables
os.environ['AWS_REGION'] = 'eu-central-1'
os.environ['BEDROCK_AGENTCORE_MEMORY_ID'] = 'test-memory-id'

# Import the agent
from test_agent import invoke

# Create a mock context class
class MockContext:
    def __init__(self):
        self.session_id = 'test-session-123'

# Run the agent with a test payload
if __name__ == "__main__":
    print("Starting test agent run...")

    payload = {
        "test": "Simple test to explore sveder.com"
    }

    context = MockContext()

    try:
        result = invoke(payload, context)
        print("\n" + "=" * 80)
        print("AGENT EXECUTION SUCCESSFUL")
        print("=" * 80)
        print(f"Result: {result}")
    except Exception as e:
        print("\n" + "=" * 80)
        print("AGENT EXECUTION FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
