from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import uuid
import boto3
import threading

# Agent configuration
AGENT_ARN = "arn:aws:bedrock-agentcore:eu-central-1:800622328366:runtime/agentcore_starter_strands-V5kqR7Ap5a"
AWS_REGION = "eu-central-1"
S3_BUCKET = "sveder-kirbuk"
S3_STAGING_PREFIX = "staging_area"


def invoke_agent_async(data, submission_id):
    """Invoke the agent asynchronously in a background thread"""
    try:
        agent_core_client = boto3.client('bedrock-agentcore', region_name=AWS_REGION)

        # Use submission_id as session_id for tracking (must be 33+ chars)
        # The UUID is 36 chars so it meets the requirement
        session_id = submission_id

        # Prepare the payload - send data directly without "input" wrapper
        payload = json.dumps(data)

        print(f"Invoking agent asynchronously with session_id: {session_id}")
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
        print(f"Error invoking agent asynchronously: {agent_error}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")


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

        # Start agent invocation in background thread
        thread = threading.Thread(target=invoke_agent_async, args=(data, submission_id))
        thread.daemon = True  # Daemon thread will not block app shutdown
        thread.start()

        print(f"Agent invocation started asynchronously for submission {submission_id}")

        # Return immediately without waiting for agent
        return JsonResponse({
            'success': True,
            'submission_id': submission_id,
            'message': 'Form submitted successfully, agent processing in background'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Error in submit_form: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def submission_status(request, submission_id):
    """Render the status page for a specific submission"""
    return render(request, 'status.html', {'submission_id': submission_id})


@csrf_exempt
def check_status(request, submission_id):
    """Check the status of a submission by looking at S3"""
    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)

        # Define the S3 paths to check
        submission_path = f"{S3_STAGING_PREFIX}/{submission_id}"
        json_key = f"{submission_path}/{submission_id}.json"
        script_key = f"{submission_path}/script.txt"
        playwright_key = f"{submission_path}/playwright.py"
        video_key = f"{submission_path}/video.webm"

        status = {
            'submission_id': submission_id,
            'json_created': False,
            'script_created': False,
            'script_content': None,
            'playwright_created': False,
            'playwright_content': None,
            'video_created': False,
            'video_url': None
        }

        # Check if JSON file exists
        try:
            s3_client.head_object(Bucket=S3_BUCKET, Key=json_key)
            status['json_created'] = True
        except s3_client.exceptions.NoSuchKey:
            pass
        except Exception as e:
            print(f"Error checking JSON file: {e}")

        # Check if script file exists and get its content
        try:
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=script_key)
            status['script_created'] = True
            status['script_content'] = response['Body'].read().decode('utf-8')
        except s3_client.exceptions.NoSuchKey:
            pass
        except Exception as e:
            print(f"Error checking script file: {e}")

        # Check if Playwright file exists and get its content
        try:
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=playwright_key)
            status['playwright_created'] = True
            status['playwright_content'] = response['Body'].read().decode('utf-8')
        except s3_client.exceptions.NoSuchKey:
            pass
        except Exception as e:
            print(f"Error checking Playwright file: {e}")

        # Check if video file exists and generate presigned URL
        try:
            s3_client.head_object(Bucket=S3_BUCKET, Key=video_key)
            status['video_created'] = True
            # Generate presigned URL valid for 1 hour
            status['video_url'] = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': S3_BUCKET, 'Key': video_key},
                ExpiresIn=3600
            )
        except s3_client.exceptions.NoSuchKey:
            pass
        except Exception as e:
            print(f"Error checking video file: {e}")

        return JsonResponse(status)

    except Exception as e:
        print(f"Error in check_status: {e}")
        return JsonResponse({'error': str(e)}, status=500)
