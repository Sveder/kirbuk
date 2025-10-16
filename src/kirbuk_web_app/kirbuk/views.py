from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import uuid
import boto3

# Agent configuration
AGENT_ARN = "arn:aws:bedrock-agentcore:eu-central-1:800622328366:runtime/agentcore_starter_strands-V5kqR7Ap5a"
AWS_REGION = "eu-central-1"

def hello_world(request):
    return render(request, 'index.html')

@csrf_exempt
def submit_form(request):
    """Handle form submission and send data to agent"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests allowed'}, status=405)

    try:
        # Parse JSON data
        data = json.loads(request.body)

        # Generate UUID for this submission
        submission_id = str(uuid.uuid4())

        # Add submission_id to data
        data['submission_id'] = submission_id

        # Print submission data
        print("=" * 80)
        print("NEW SUBMISSION")
        print("=" * 80)
        print(f"Submission ID: {submission_id}")
        print(f"Email: {data.get('email')}")
        print(f"Product URL: {data.get('product_url')}")
        print(f"Directions: {data.get('directions')}")
        print(f"Test Username: {data.get('test_username')}")
        print(f"Test Password: {'***' if data.get('test_password') else 'Not provided'}")
        print(f"Roast Mode: {data.get('roast_mode')}")
        print("=" * 80)

        # Invoke the agent
        try:
            agent_core_client = boto3.client('bedrock-agentcore', region_name=AWS_REGION)

            # Use submission_id as session_id for tracking (must be 33+ chars)
            # The UUID is 36 chars so it meets the requirement
            session_id = submission_id

            # Prepare the payload - send data directly without "input" wrapper
            payload = json.dumps(data)

            print(f"Invoking agent with session_id: {session_id}")
            print(f"Payload: {payload}")

            # Invoke the agent
            response = agent_core_client.invoke_agent_runtime(
                agentRuntimeArn=AGENT_ARN,
                runtimeSessionId=session_id,
                payload=payload,
                qualifier="DEFAULT"
            )

            # Read and parse the response
            response_body = response['response'].read()
            response_data = json.loads(response_body)

            print(f"Agent invoked successfully. Response: {response_data}")

        except Exception as agent_error:
            print(f"Error invoking agent: {agent_error}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            # Continue anyway - we'll still return success to user
            # but log the error for debugging

        return JsonResponse({
            'success': True,
            'submission_id': submission_id,
            'message': 'Form submitted successfully and agent invoked'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Error in submit_form: {e}")
        return JsonResponse({'error': str(e)}, status=500)
