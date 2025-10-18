"""
Strands Agent sample with AgentCore
"""
import os
import json
import boto3
import sentry_sdk
from strands import Agent
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

SYSTEM_PROMPT = """You are an agent that goes over SaaS products and helps create demo videos.
You will be given a website URL and instruction and you will need to explore the website and understand
what is the user flow through it and main functionality.

Your response should be a script for what to do on website to best showcase the main features.

IMPORTANT TIMING: Create a script that will take approximately 2 minutes to demonstrate.
- Include enough steps to fill 2 minutes of screen time
- Each action takes 3-5 seconds, so plan for about 24-40 actions total
- Include pauses where needed to let information sink in

More rules:
1. If the site throws an error, note it but continue your exploration.
2. If you find settings - look at them but do not try to change settings.
3. If provided with a username and password, use it to login to the site. Do not try to create a new account.
4. Dismiss any cookie popups with allow all option or similar.
5. If you seem stuck go back to the starting page and start over, this time only following the main path.
6. If there is a documentation page - look at main page only and don't read all the docs. Definitely don't search the logs.
7. Don't stop with errors ever. Instead restart and try again once and if not just stop regularly with suitable message.
"""

ci_sessions = {}
current_session = None


def save_payload_to_s3(payload, submission_id):
    """Save the payload to S3 in the staging area"""
    try:
        s3_client = boto3.client('s3', region_name=REGION)

        # Create the S3 key: staging_area/<uuid>/<uuid>.json
        s3_key = f"{S3_STAGING_PREFIX}/{submission_id}/{submission_id}.json"

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


def save_script_to_s3(script, submission_id):
    """Save the script to S3 in the staging area"""
    try:
        s3_client = boto3.client('s3', region_name=REGION)

        # Create the S3 key: staging_area/<uuid>/script.txt
        s3_key = f"{S3_STAGING_PREFIX}/{submission_id}/script.txt"

        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=script,
            ContentType='text/plain'
        )

        print(f"Successfully saved script to s3://{S3_BUCKET}/{s3_key}")
        return s3_key

    except Exception as e:
        print(f"Error saving script to S3: {e}")
        raise


def save_playwright_to_s3(playwright_code, submission_id):
    """Save the Playwright script to S3 in the staging area"""
    try:
        s3_client = boto3.client('s3', region_name=REGION)

        # Create the S3 key: staging_area/<uuid>/playwright.py
        s3_key = f"{S3_STAGING_PREFIX}/{submission_id}/playwright.py"

        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=playwright_code,
            ContentType='text/x-python'
        )

        print(f"Successfully saved Playwright script to s3://{S3_BUCKET}/{s3_key}")
        return s3_key

    except Exception as e:
        print(f"Error saving Playwright script to S3: {e}")
        raise


def save_video_to_s3(video_path, submission_id):
    """Save the video to S3 in the staging area"""
    try:
        s3_client = boto3.client('s3', region_name=REGION)

        # Create the S3 key: staging_area/<uuid>/video.webm
        s3_key = f"{S3_STAGING_PREFIX}/{submission_id}/video.webm"

        # Read video file
        with open(video_path, 'rb') as video_file:
            video_data = video_file.read()

        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=video_data,
            ContentType='video/webm'
        )

        print(f"Successfully saved video to s3://{S3_BUCKET}/{s3_key}")
        return s3_key

    except Exception as e:
        print(f"Error saving video to S3: {e}")
        raise


def merge_audio_video_with_ffmpeg(video_path, audio_path, output_path):
    """Merge audio and video files using FFmpeg

    Args:
        video_path: Path to the input video file (webm)
        audio_path: Path to the input audio file (mp3)
        output_path: Path for the output video file (webm with audio)

    Returns:
        Path to the output file
    """
    import subprocess

    try:
        print(f"Merging audio and video with FFmpeg...")
        print(f"Video: {video_path}")
        print(f"Audio: {audio_path}")
        print(f"Output: {output_path}")

        # FFmpeg command to merge audio and video
        # -i: input files
        # -c:v copy: copy video codec without re-encoding (fast)
        # -c:a libopus: convert audio to Opus codec (WebM compatible)
        # -shortest: finish encoding when shortest input stream ends
        cmd = [
            'ffmpeg',
            '-i', video_path,        # Input video
            '-i', audio_path,        # Input audio
            '-c:v', 'copy',          # Copy video without re-encoding
            '-c:a', 'libopus',       # Convert audio to Opus for WebM
            '-shortest',             # Match shortest duration
            '-y',                    # Overwrite output file if exists
            output_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        if result.returncode != 0:
            print(f"FFmpeg stderr: {result.stderr}")
            raise Exception(f"FFmpeg failed with return code {result.returncode}: {result.stderr}")

        print(f"Successfully merged audio and video: {output_path}")
        return output_path

    except subprocess.TimeoutExpired:
        print("FFmpeg merge timed out after 2 minutes")
        raise Exception("FFmpeg merge timed out")
    except Exception as e:
        print(f"Error merging audio and video: {e}")
        raise


def save_voice_script_to_s3(voice_script, submission_id):
    """Save the SSML voice script to S3 in the staging area"""
    try:
        s3_client = boto3.client('s3', region_name=REGION)

        # Create the S3 key: staging_area/<uuid>/voice_script.ssml
        s3_key = f"{S3_STAGING_PREFIX}/{submission_id}/voice_script.ssml"

        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=voice_script,
            ContentType='application/ssml+xml'
        )

        print(f"Successfully saved voice script to s3://{S3_BUCKET}/{s3_key}")
        return s3_key

    except Exception as e:
        print(f"Error saving voice script to S3: {e}")
        raise


def synthesize_voice_with_polly(voice_script, submission_id):
    """Synthesize voice from SSML script using AWS Polly async API with Matthew voice and generative engine"""
    import time

    try:
        polly_client = boto3.client('polly', region_name=REGION)

        print("Starting async voice synthesis with AWS Polly (Matthew voice, generative engine)...")
        print(f"Voice script length: {len(voice_script)} characters")

        # Start asynchronous synthesis task
        # Polly will write the MP3 directly to S3
        response = polly_client.start_speech_synthesis_task(
            Engine='generative',  # Use generative engine for more natural speech
            VoiceId='Matthew',    # Male voice
            OutputFormat='mp3',
            TextType='ssml',
            Text=voice_script,
            OutputS3BucketName=S3_BUCKET,
            OutputS3KeyPrefix=f"{S3_STAGING_PREFIX}/{submission_id}/"
        )

        task_id = response['SynthesisTask']['TaskId']
        print(f"Synthesis task started with ID: {task_id}")

        # Poll for task completion
        max_wait_time = 300  # 5 minutes max
        poll_interval = 2    # Poll every 2 seconds
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            task_status = polly_client.get_speech_synthesis_task(TaskId=task_id)
            task = task_status['SynthesisTask']
            status = task['TaskStatus']

            print(f"Synthesis status: {status} (elapsed: {elapsed_time}s)")

            if status == 'completed':
                output_uri = task['OutputUri']
                print(f"✓ Voice synthesis completed successfully")
                print(f"Output URI: {output_uri}")

                # Parse the S3 key from the OutputUri
                # Format: https://s3.region.amazonaws.com/bucket/key or
                #         https://bucket.s3.region.amazonaws.com/key
                import urllib.parse
                parsed = urllib.parse.urlparse(output_uri)
                # Extract key from path (remove leading /)
                polly_s3_key = parsed.path.lstrip('/')
                # If bucket is in hostname, we need to handle that
                if S3_BUCKET in parsed.netloc:
                    # Format is bucket.s3.region.amazonaws.com/key
                    polly_s3_key = parsed.path.lstrip('/')
                else:
                    # Format is s3.region.amazonaws.com/bucket/key
                    # Remove bucket name from path
                    path_parts = parsed.path.lstrip('/').split('/', 1)
                    if len(path_parts) > 1:
                        polly_s3_key = path_parts[1]

                print(f"Polly created file at S3 key: {polly_s3_key}")

                # Our expected key
                s3_key = f"{S3_STAGING_PREFIX}/{submission_id}/voice.mp3"

                # Copy to our expected filename
                s3_client = boto3.client('s3', region_name=REGION)
                s3_client.copy_object(
                    Bucket=S3_BUCKET,
                    CopySource={'Bucket': S3_BUCKET, 'Key': polly_s3_key},
                    Key=s3_key
                )
                print(f"✓ Renamed synthesis output from {polly_s3_key} to {s3_key}")

                # Delete the original Polly file
                s3_client.delete_object(Bucket=S3_BUCKET, Key=polly_s3_key)
                print(f"✓ Deleted temporary file: {polly_s3_key}")

                return s3_key

            elif status == 'failed':
                reason = task.get('TaskStatusReason', 'Unknown reason')
                raise Exception(f"Polly synthesis task failed: {reason}")

            # Wait before next poll
            time.sleep(poll_interval)
            elapsed_time += poll_interval

        # Timeout
        raise Exception(f"Polly synthesis task timed out after {max_wait_time} seconds")

    except Exception as e:
        print(f"Error synthesizing voice with Polly: {e}")
        raise


def generate_voice_script(script_text, product_url):
    """Generate an SSML voice script from the narrative script"""
    try:
        # Create a simple agent without tools to generate the SSML voice script
        agent = Agent(
            model=MODEL_ID,
            system_prompt="""You are an expert at creating SSML (Speech Synthesis Markup Language) voice scripts for demo videos using AWS Polly Generative engine.

IMPORTANT TIMING: Create a narration that will take approximately 2 minutes to speak.
- Aim for 250-300 words total (typical speaking rate is 130-150 words per minute)
- Include strategic pauses to allow viewers to absorb what they're seeing
- The narration should match the pacing of the on-screen actions

IMPORTANT - Only use these SSML tags (fully supported by Polly Generative):
- <speak> - Root element (required)
- <break> - Add pauses (use time="500ms" or strength="medium")
- <lang> - Specify language for specific words
- <p> - Paragraph pauses
- <s> - Sentence boundaries
- <say-as> - Control how special words are spoken
- <sub> - Substitute pronunciation
- <w> - Specify parts of speech

DO NOT USE these tags (not supported by Polly Generative):
- <emphasis> - NOT AVAILABLE
- <prosody> - Only partially available, AVOID
- <phoneme> - Only partially available, AVOID
- <mark> - Only partially available, AVOID

Requirements:
1. Use proper SSML syntax with <speak> root element
2. Use <break> tags for pauses at appropriate moments (e.g., <break time="500ms"/> or <break strength="medium"/>)
3. Use <s> tags for sentence boundaries
4. Use <p> tags for paragraph breaks
5. Make the voice-over engaging, clear, and professional
6. Focus on explaining what the viewer is seeing and why it matters
7. Keep sentences concise and easy to understand when spoken
8. Return ONLY the SSML code, no explanations or markdown
9. Add appropriate pauses between sections using <break>
10. Time the narration to match the ~2 minute video duration

The voice-over should guide the viewer through the demo, explaining features and benefits naturally."""
        )

        prompt = f"""Create an SSML voice-over script for a demo video of this website: {product_url}

The demo follows this narrative:
{script_text}

Create an engaging voice-over that explains what's happening in the demo and highlights the key features and benefits.
Return only the SSML code, nothing else."""

        result = agent(prompt)
        voice_script = result.message.get('content', [{}])[0].get('text', str(result))

        # Clean up the code if it has markdown code blocks
        if '```xml' in voice_script:
            voice_script = voice_script.split('```xml')[1].split('```')[0].strip()
        elif '```ssml' in voice_script:
            voice_script = voice_script.split('```ssml')[1].split('```')[0].strip()
        elif '```' in voice_script:
            voice_script = voice_script.split('```')[1].split('```')[0].strip()

        # Ensure it starts with <?xml and has <speak> tags
        if not voice_script.startswith('<?xml'):
            voice_script = '<?xml version="1.0"?>\n' + voice_script

        if '<speak>' not in voice_script:
            # Wrap in speak tags if missing
            voice_script = voice_script.replace('<?xml version="1.0"?>\n', '<?xml version="1.0"?>\n<speak>\n') + '\n</speak>'

        return voice_script

    except Exception as e:
        print(f"Error generating voice script: {e}")
        raise


def generate_playwright_script(script_text, product_url, additional_directions=None):
    """Generate a Playwright Python script from the narrative script"""
    try:
        # Create a simple agent without tools to generate the Playwright script
        agent = Agent(
            model=MODEL_ID,
            system_prompt="""You are an expert at creating Playwright Python scripts for web automation and demo video creation.
Given a narrative script of what to do on a website, create a complete, runnable Playwright Python script.
Make sure the script is configured to save videos using context.record_video_dir="videos/" and context.record_video_size={"width": 1280, "height":720}.

IMPORTANT TIMING: The script should create a video that is approximately 2 minutes long.
- Each action (click, type, navigate) takes 3-5 seconds on screen
- Add page.wait_for_timeout() calls between actions to let content be visible (typically 2000-4000ms)
- Target 24-40 total actions to fill 2 minutes
- The video timing should synchronize with a ~2 minute voice narration
- Include longer pauses (3-5 seconds) after important sections to let information sink in

Requirements:
1. Use async Playwright with Python
2. Include proper imports and setup
3. Add appropriate waits and error handling - use page.wait_for_timeout() liberally
4. Include comments explaining each step
5. Make the script record video to 'output.webm' file
6. Return ONLY the Python code, no explanations
7. Use proper selectors (prefer data-testid, then role, then css)
8. Handle common issues like popups, cookies, etc.
9. The script MUST save video as 'output.webm' in current directory
10. Pace the actions to create a ~2 minute video that matches the voice narration timing
"""
        )

        prompt = f"""Create a Playwright Python script for the following website: {product_url}

The script should follow this narrative:
{script_text}"""

        if additional_directions:
            prompt += f"""

Additional user directions to incorporate:
{additional_directions}"""

        prompt += "\n\nIMPORTANT: The script MUST record video and save it as 'output.webm'. Return only the Python code, nothing else."

        result = agent(prompt)
        playwright_code = result.message.get('content', [{}])[0].get('text', str(result))

        # Clean up the code if it has markdown code blocks
        if '```python' in playwright_code:
            playwright_code = playwright_code.split('```python')[1].split('```')[0].strip()
        elif '```' in playwright_code:
            playwright_code = playwright_code.split('```')[1].split('```')[0].strip()

        return playwright_code

    except Exception as e:
        print(f"Error generating Playwright script: {e}")
        raise


def execute_playwright_script(playwright_code, submission_id):
    """Execute the Playwright script, merge audio with video, and upload the resulting video to S3"""
    import tempfile
    import subprocess

    try:
        # Create a temporary directory for execution
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Executing Playwright script in {temp_dir}")

            # Write the script to a file
            script_path = os.path.join(temp_dir, 'playwright_script.py')
            with open(script_path, 'w') as f:
                f.write(playwright_code)

            # Execute the script
            print("Running Playwright script...")
            result = subprocess.run(
                ['python', script_path],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            print(f"Script execution stdout: {result.stdout}")
            if result.stderr:
                print(f"Script execution stderr: {result.stderr}")

            if result.returncode != 0:
                raise Exception(f"Playwright script failed with return code {result.returncode}: {result.stderr}")

            # Check if video was created
            video_path = os.path.join(temp_dir, 'output.webm')
            if not os.path.exists(video_path):
                raise Exception("Video file 'output.webm' was not created by the script")

            # Try to download audio from S3 and merge it with the video
            print("\n" + "-" * 80)
            print("STEP 6.1: Attempting to merge audio with video")
            print("-" * 80)
            try:
                s3_client = boto3.client('s3', region_name=REGION)
                audio_s3_key = f"{S3_STAGING_PREFIX}/{submission_id}/voice.mp3"
                audio_path = os.path.join(temp_dir, 'voice.mp3')

                print(f"→ Downloading audio from S3: {audio_s3_key}")
                s3_client.download_file(S3_BUCKET, audio_s3_key, audio_path)
                print(f"✓ Audio downloaded successfully (size: {os.path.getsize(audio_path)} bytes)")

                # Merge audio and video
                merged_video_path = os.path.join(temp_dir, 'output_with_audio.webm')
                print(f"→ Merging audio and video with FFmpeg...")
                merge_audio_video_with_ffmpeg(video_path, audio_path, merged_video_path)

                # Use the merged video as the final video
                video_path = merged_video_path
                print(f"✓ Audio and video merged successfully (size: {os.path.getsize(video_path)} bytes)")

            except s3_client.exceptions.NoSuchKey:
                print(f"⚠ No audio file found in S3 at {audio_s3_key}, uploading video without audio")
            except Exception as merge_error:
                print(f"✗ Error merging audio with video: {merge_error}")
                print("⚠ Uploading video without audio")
                import traceback
                print(f"Audio merge traceback: {traceback.format_exc()}")

            # Upload final video to S3
            print("\n" + "-" * 80)
            print("STEP 6.2: Uploading final video to S3")
            print("-" * 80)
            s3_key = save_video_to_s3(video_path, submission_id)
            print(f"✓ Video uploaded to S3: {s3_key}")

            return s3_key

    except subprocess.TimeoutExpired:
        print("Playwright script execution timed out after 5 minutes")
        raise Exception("Script execution timed out")
    except Exception as e:
        print(f"Error executing Playwright script: {e}")
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

        # Note: Memory session manager removed to avoid throttling issues
        # Each job is independent and doesn't need persistent memory
        session_id = getattr(context, 'session_id', 'default')
        current_session = session_id

        browser_tool = AgentCoreBrowser(
            region=REGION,
            identifier=KIRBUK_BROWSER_IDENTIFIER
        )

        # Create agent without memory session manager to avoid throttling
        agent = Agent(
            model=MODEL_ID,
            system_prompt=SYSTEM_PROMPT,
            tools=[browser_tool.browser]
        )

        prompt = f"Visit website {payload['product_url']}. Additional user instructions: {payload['directions']}."
        if payload.get('test_username') and payload.get('test_password'):
            prompt += f" Use username/email '{payload['test_username']}' and password '{payload['test_password']}' to login to the site."

        print("=" * 80)
        print("STEP 1: Invoking agent to explore website")
        print("=" * 80)
        result = agent(prompt)
        print("✓ Agent exploration completed")

        print("\nClosing browser platform...")
        browser_tool.close_platform()
        print("✓ Browser closed")

        response = result.message.get('content', [{}])[0].get('text', str(result))
        print(f"\n{'=' * 80}")
        print(f"Agent Response Length: {len(response)} characters")
        print(f"{'=' * 80}")

        # Save script to S3 before returning
        if submission_id and response:
            print("\n" + "=" * 80)
            print("STEP 2: Saving narrative script to S3")
            print("=" * 80)
            script_s3_key = save_script_to_s3(response, submission_id)
            print(f"✓ Script saved to S3: {script_s3_key}")

            # Generate and save voice script
            print("\n" + "=" * 80)
            print("STEP 3: Generating SSML voice script")
            print("=" * 80)
            voice_script = None
            try:
                voice_script = generate_voice_script(response, payload['product_url'])
                print(f"✓ Voice script generated ({len(voice_script)} characters)")

                voice_script_s3_key = save_voice_script_to_s3(voice_script, submission_id)
                print(f"✓ Voice script saved to S3: {voice_script_s3_key}")

                # Synthesize voice using AWS Polly
                print("\n" + "=" * 80)
                print("STEP 4: Synthesizing voice with AWS Polly")
                print("=" * 80)
                try:
                    voice_audio_s3_key = synthesize_voice_with_polly(voice_script, submission_id)
                    print(f"✓ Voice audio synthesized and saved to S3: {voice_audio_s3_key}")
                except Exception as polly_error:
                    print(f"✗ Error synthesizing voice with Polly: {polly_error}")
                    import traceback
                    print(f"Polly synthesis traceback: {traceback.format_exc()}")

            except Exception as voice_error:
                print(f"✗ Error generating voice script: {voice_error}")
                # Don't fail the entire job if voice script generation fails
                import traceback
                print(f"Voice script generation traceback: {traceback.format_exc()}")

            # Generate and save Playwright script
            print("\n" + "=" * 80)
            print("STEP 5: Generating Playwright script")
            print("=" * 80)
            playwright_code = generate_playwright_script(
                response,
                payload['product_url'],
                payload.get('directions')
            )
            print(f"✓ Playwright script generated ({len(playwright_code)} characters)")

            playwright_s3_key = save_playwright_to_s3(playwright_code, submission_id)
            print(f"✓ Playwright script saved to S3: {playwright_s3_key}")

            # Save generated Playwright code to a file for debugging/local use
            if playwright_code:
                debug_script_path = f"/tmp/playwright_script_{submission_id}.py"
                try:
                    with open(debug_script_path, "w", encoding="utf-8") as f:
                        f.write(playwright_code)
                    print(f"✓ Playwright code also saved locally at: {debug_script_path}")
                except Exception as file_save_exc:
                    print(f"✗ Warning: Failed to save playwright script to file: {file_save_exc}")

            # Execute the Playwright script and upload video
            print("\n" + "=" * 80)
            print("STEP 6: Executing Playwright script to create video")
            print("=" * 80)
            try:
                video_s3_key = execute_playwright_script(playwright_code, submission_id)
                print(f"✓ Video successfully created and uploaded to S3: {video_s3_key}")
            except Exception as video_error:
                print(f"✗ Error creating video: {video_error}")
                # Don't fail the entire job if video creation fails
                import traceback
                print(f"Video creation traceback: {traceback.format_exc()}")

        print("\n" + "=" * 80)
        print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"Submission ID: {submission_id}")
        print("=" * 80)

        return {"response": response}

    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ WORKFLOW FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        print("=" * 80)

        # Capture exception in Sentry with context
        sentry_sdk.set_context("payload", payload)
        sentry_sdk.set_context("session", {
            "session_id": current_session
        })
        sentry_sdk.capture_exception(e)

        # Re-raise the exception to let the framework handle it
        raise

if __name__ == "__main__":
    app.run()
