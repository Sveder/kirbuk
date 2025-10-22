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
SOURCE_EMAIL = os.getenv("SOURCE_EMAIL", "Kirbuk <m@sveder.com>")  # Verified SES sender email with display name

def get_exploration_system_prompt(roast_mode=False):
    """Generate system prompt for website exploration based on mode

    Args:
        roast_mode: If True, use humorous/critical tone; if False, use professional tone

    Returns:
        System prompt string
    """
    tone_instructions = ""
    if roast_mode:
        tone_instructions = """
TONE - ROAST MODE ENABLED:
Your script should be HUMOROUS, SARCASTIC, and CRITICAL. This is "roast mode"!
- Point out confusing UI/UX choices with humor
- Make playful jokes about unnecessary complexity
- Be witty about questionable design decisions
- Comment sarcastically on things that don't work well
- Still be informative, but with comedic flair
- Keep it fun and entertaining, not mean-spirited
- Example: "And here's where they hid the settings button... because who needs easy access to settings, right?"
"""
    else:
        tone_instructions = """
TONE - PROFESSIONAL MODE:
Your script should be PROFESSIONAL, INFORMATIVE, and POSITIVE.
- Highlight features and benefits
- Explain functionality clearly
- Maintain an encouraging, helpful tone
- Focus on what works well
"""

    return f"""You are an agent that goes over SaaS products and helps create demo videos.
You will be given a website URL and instruction and you will need to explore the website and understand
what is the user flow through it and main functionality.

Your response should be a script for what to do on website to best showcase the main features.
{tone_instructions}

IMPORTANT TIMING: Create a script that will take approximately 2 minutes to demonstrate.
- Include enough steps to fill 2 minutes of screen time
- Each action takes 3-5 seconds, so plan for about 24-40 actions total
- Include pauses where needed to let information sink in

CRITICAL - WHEN TO STOP EXPLORING:
- Explore for a MAXIMUM of 10-15 browser actions (clicks, navigations, form fills)
- After you understand the main features, STOP exploring and write your final script
- Do NOT endlessly click around the site - focus on the key user journey
- If you've seen the main features, FINISH your exploration and provide the script
- You should spend no more than 5-10 minutes total on exploration

IMPORTANT - CAPTURE DETAILED SELECTOR INFORMATION:
When exploring the website, pay close attention to interactive elements and note:
- Visible button text and labels (e.g., "Sign Up", "Get Started", "Add to Cart")
- Placeholder text in input fields (e.g., "Enter your email", "Search...")
- ARIA labels and roles when visible (e.g., role="button", aria-label="Close")
- Unique identifiers like data-testid attributes when present
- Descriptive class names that indicate purpose (e.g., "login-button", "nav-menu", "submit-form")
- Element types and their context (e.g., "the blue button in the top right", "first input in the form")

In your final script, include this selector information to help create robust Playwright scripts.
For example, instead of just saying "click the submit button", say "click the submit button (text='Submit' or button with class 'submit-btn')".

More rules:
1. If the site throws an error, note it but continue your exploration.
2. If you find settings - look at them but do not try to change settings.
3. If provided with a username and password, use it to login to the site. Do not try to create a new account.
4. Dismiss any cookie popups with allow all option or similar.
5. If you seem stuck go back to the starting page and start over, this time only following the main path.
6. If there is a documentation page - look at main page only and don't read all the docs. Definitely don't search the logs.
7. Don't stop with errors ever. Instead restart and try again once and if not just stop regularly with suitable message.
8. After 10-15 actions, you MUST stop exploring and write your final demo script - do not continue clicking endlessly.
9. When describing interactive elements in your script, always include multiple selector options (text, role, class, placeholder) to make Playwright scripts more reliable.
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


def merge_audio_video_with_music(video_path, audio_path, music_path, output_path,
                                  voice_volume=1.0, music_volume=0.15):
    """Merge video, voice audio, and background music with volume control

    Args:
        video_path: Path to the input video file (webm)
        audio_path: Path to the voice audio file (mp3)
        music_path: Path to the background music file (mp3)
        output_path: Path for the output video file (webm with audio)
        voice_volume: Volume level for voice (default 1.0 = 100%)
        music_volume: Volume level for background music (default 0.15 = 15%)

    Returns:
        Path to the output file
    """
    import subprocess

    try:
        print(f"Merging video, voice, and background music with FFmpeg...")
        print(f"Video: {video_path}")
        print(f"Voice: {audio_path} (volume: {voice_volume})")
        print(f"Music: {music_path} (volume: {music_volume})")
        print(f"Output: {output_path}")

        # FFmpeg command to merge video with mixed audio (voice + background music)
        # Filter complex:
        # 1. Apply volume to voice track
        # 2. Apply volume to music track and loop it
        # 3. Mix both audio tracks together
        cmd = [
            'ffmpeg',
            '-i', video_path,                    # Input 0: video
            '-i', audio_path,                    # Input 1: voice
            '-stream_loop', '-1',                # Loop music indefinitely
            '-i', music_path,                    # Input 2: background music
            '-filter_complex',
            f'[1:a]volume={voice_volume}[voice];'  # Voice at specified volume
            f'[2:a]volume={music_volume}[music];'  # Music at specified volume
            '[voice][music]amix=inputs=2:duration=first[audio]',  # Mix both, use voice duration
            '-map', '0:v',                       # Use video from input 0
            '-map', '[audio]',                   # Use mixed audio
            '-c:v', 'copy',                      # Copy video without re-encoding
            '-c:a', 'libopus',                   # Encode audio to Opus for WebM
            '-shortest',                         # Match shortest stream duration
            '-y',                                # Overwrite output file if exists
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

        print(f"✓ Successfully merged video with voice and background music: {output_path}")
        return output_path

    except subprocess.TimeoutExpired:
        print("FFmpeg audio mixing timed out after 2 minutes")
        raise Exception("Audio mixing timed out")
    except Exception as e:
        print(f"Error merging audio and video with music: {e}")
        raise


def merge_audio_video_with_ffmpeg(video_path, audio_path, output_path):
    """Merge audio and video files using FFmpeg (without background music)

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


def get_video_duration(video_path):
    """Get the duration of a video file in seconds using ffprobe

    Args:
        video_path: Path to the video file

    Returns:
        Duration in seconds (float)
    """
    import subprocess
    import json

    try:
        # Use ffprobe to get video duration
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            video_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise Exception(f"ffprobe failed: {result.stderr}")

        data = json.loads(result.stdout)
        duration = float(data['format']['duration'])

        print(f"✓ Video duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        return duration

    except Exception as e:
        print(f"Error getting video duration: {e}")
        # Return default 2 minutes if we can't measure
        print("⚠️  Defaulting to 120 seconds (2 minutes)")
        return 120.0


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


def send_email_notification(subject, body, recipient_email, submission_id=None):
    """Send email notification using AWS SES

    Args:
        subject: Email subject line
        body: Email body text
        recipient_email: The user's email address to send to
        submission_id: Optional submission ID for status link
    """
    try:
        ses_client = boto3.client('ses', region_name=REGION)

        # Build the styled HTML email body matching web app colors
        html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background-color: #8B4513;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        .card {{
            background-color: #A0522D;
            border: 2px solid #D2691E;
            border-radius: 8px;
            padding: 30px;
            color: #FFF8DC;
        }}
        h1 {{
            color: #FFF8DC;
            font-size: 28px;
            margin: 0 0 20px 0;
        }}
        p {{
            color: #FFF8DC;
            font-size: 16px;
            line-height: 1.6;
            margin: 0 0 15px 0;
        }}
        .button {{
            display: inline-block;
            padding: 12px 24px;
            background-color: #D2691E;
            color: #FFF8DC;
            text-decoration: none;
            border-radius: 4px;
            font-weight: 600;
            font-size: 16px;
            margin-top: 20px;
        }}
        .button:hover {{
            background-color: #CD853F;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            color: #FFF8DC;
            opacity: 0.8;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>{subject}</h1>
            <p>{body}</p>
"""
        if submission_id:
            status_url = f"https://kirbuk.sveder.com/submission/{submission_id}"
            html_body += f"""            <a href="{status_url}" class="button">View Status</a>
"""

        html_body += """        </div>
        <div class="footer">
            <p>Kirbuk - Automated SaaS Product Videos</p>
        </div>
    </div>
</body>
</html>"""

        text_body = f"{subject}\n\n{body}"
        if submission_id:
            text_body += f"\n\nView submission status: https://kirbuk.sveder.com/submission/{submission_id}"

        response = ses_client.send_email(
            Source=SOURCE_EMAIL,
            Destination={
                'ToAddresses': [recipient_email],
                'BccAddresses': ['m@sveder.com']
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': text_body,
                        'Charset': 'UTF-8'
                    },
                    'Html': {
                        'Data': html_body,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )

        print(f"✓ Email sent successfully: {subject}")
        print(f"  Message ID: {response['MessageId']}")
        return response

    except Exception as e:
        print(f"✗ Error sending email: {e}")
        # Don't fail the workflow if email fails
        import traceback
        print(f"Email error traceback: {traceback.format_exc()}")


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


def generate_voice_script(script_text, product_url, video_duration_seconds=120, roast_mode=False, playwright_script=None):
    """Generate an SSML voice script from the narrative script and Playwright code

    Args:
        script_text: The narrative script from browser exploration
        product_url: URL of the product being demoed
        video_duration_seconds: Exact duration of the video in seconds (default 120)
        roast_mode: If True, use humorous/sarcastic tone; if False, use professional tone
        playwright_script: The generated Playwright script code (optional but recommended)

    Returns:
        SSML voice script string
    """
    try:
        # Calculate word count based on duration (130-150 words per minute)
        minutes = video_duration_seconds / 60
        target_words_min = int(130 * minutes)
        target_words_max = int(150 * minutes)

        # Add tone instructions based on mode
        tone_instructions = ""
        if roast_mode:
            tone_instructions = """
TONE - ROAST MODE:
- Use a HUMOROUS, SARCASTIC, and WITTY tone
- Point out funny quirks and questionable design choices
- Be playfully critical while still being informative
- Add comedic commentary and jokes
- Keep it entertaining and fun, not mean
- Example tone: "And here we have... wait for it... another settings menu. Because one wasn't enough!"
"""
        else:
            tone_instructions = """
TONE - PROFESSIONAL MODE:
- Use a PROFESSIONAL, CLEAR, and POSITIVE tone
- Focus on features and benefits
- Be encouraging and helpful
- Maintain an informative, friendly delivery
"""

        # Create a simple agent without tools to generate the SSML voice script
        agent = Agent(
            model=MODEL_ID,
            system_prompt=f"""You are an expert at creating SSML (Speech Synthesis Markup Language) voice scripts for demo videos using AWS Polly Generative engine.

CRITICAL TIMING REQUIREMENT: The video is EXACTLY {video_duration_seconds:.1f} seconds ({minutes:.2f} minutes) long.
Your narration MUST match this exact duration:
- Aim for {target_words_min}-{target_words_max} words total (typical speaking rate is 130-150 words per minute)
- Include strategic pauses to allow viewers to absorb what they're seeing
- The narration should fill the entire video duration without going over
- Use <break> tags to add pauses and stretch the narration to match the video length
{tone_instructions}

CRITICAL - ONLY use these SSML tags (fully supported by Polly Generative):
- <speak> - Root element (required)
- <break> - Add pauses (use time="500ms" or strength="medium")
- <lang> - Specify language for specific words
- <p> - Paragraph pauses
- <s> - Sentence boundaries
- <say-as> - Control how special words are spoken
- <sub> - Substitute pronunciation
- <w> - Specify parts of speech

ABSOLUTELY DO NOT USE these tags (WILL CAUSE ERRORS):
- <emphasis> - NOT SUPPORTED - will cause InvalidSsmlException
- <prosody> - NOT SUPPORTED - will cause InvalidSsmlException
- <phoneme> - NOT SUPPORTED - will cause InvalidSsmlException
- <mark> - NOT SUPPORTED - will cause InvalidSsmlException
- <amazon:effect> - NOT SUPPORTED - will cause InvalidSsmlException
- <amazon:domain> - NOT SUPPORTED - will cause InvalidSsmlException
- <amazon:emotion> - NOT SUPPORTED - will cause InvalidSsmlException
- <amazon:auto-breaths> - NOT SUPPORTED - will cause InvalidSsmlException

If you need emphasis, use natural language and word choice instead of <emphasis> tags.
If you need prosody changes, use natural phrasing and punctuation instead of <prosody> tags.

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

        # Build prompt with narrative and optionally Playwright script
        prompt = f"""Create an SSML voice-over script for a demo video of this website: {product_url}

The demo follows this narrative:
{script_text}"""

        # Add Playwright script if available for better synchronization
        if playwright_script:
            prompt += f"""

IMPORTANT - Synchronize with Playwright Script:
The video is created from this Playwright automation script. Use it to understand the EXACT actions and timing:

```python
{playwright_script}
```

Your narration should:
1. Match the sequence of actions in the Playwright script
2. Describe what's happening as each action executes
3. Time pauses to align with page.wait_for_timeout() calls
4. Explain what the user is seeing at each step
5. Use the wait times in the script to pace your narration accordingly"""

        prompt += """

Create an engaging voice-over that:
- Follows the exact flow of actions in the Playwright script
- Explains what's happening in the demo at each step
- Highlights key features and benefits as they appear
- Times the narration to match the video pacing

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

        # Sanitize SSML - remove tags that are NOT supported by Polly Generative
        import re

        # Tags to remove completely (not supported by Polly Generative)
        unsupported_tags = [
            'emphasis',
            'prosody',
            'phoneme',
            'mark',
            'amazon:effect',
            'amazon:domain',
            'amazon:emotion',
            'amazon:auto-breaths'
        ]

        for tag in unsupported_tags:
            # Remove opening tags with any attributes
            voice_script = re.sub(rf'<{tag}[^>]*>', '', voice_script, flags=re.IGNORECASE)
            # Remove closing tags
            voice_script = re.sub(rf'</{tag}>', '', voice_script, flags=re.IGNORECASE)

        print(f"✓ SSML sanitized - removed unsupported tags")

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

CRITICAL - ROBUST SELECTOR STRATEGIES:
When the narrative script provides selector hints (text, class names, roles, placeholders), use a fallback approach:
1. First, try the most specific selector (data-testid, id, or specific text)
2. Add try/except blocks with alternative selectors as fallbacks
3. Use .first when multiple elements might match
4. Add wait_for(state="visible") before clicking/typing
5. Use role-based selectors when mentioned (e.g., getByRole('button', name='Submit'))

Example robust selector approach:
```python
try:
    # Try specific selector first
    button = page.locator("button:has-text('Sign Up')").first
    await button.wait_for(state="visible", timeout=5000)
    await button.click()
except:
    # Fallback to class or role
    try:
        button = page.locator(".signup-btn, [role='button']:has-text('Sign')").first
        await button.click()
    except:
        # Final fallback - find any button with partial text
        button = page.get_by_role("button", name=re.compile("sign.*up", re.I)).first
        await button.click()
```

Requirements:
1. Use async Playwright with Python
2. Include proper imports and setup
3. Add appropriate waits and error handling - use page.wait_for_timeout() liberally
4. Include comments explaining each step
5. Make the script record video to 'output.webm' file
6. Return ONLY the Python code, no explanations
7. Use multiple selector strategies with fallbacks (text > role > class > generic)
8. Handle common issues like popups, cookies, etc.
9. The script MUST save video as 'output.webm' in current directory
10. Pace the actions to create a ~2 minute video that matches the voice narration timing
11. Set browser locale to English and include Accept-Language header to ensure website displays in English:
    - Use locale='en-US' in browser.new_context()
    - Set extra_http_headers={'Accept-Language': 'en-US,en;q=0.9'} in browser.new_context()
12. Always use .first when selecting elements to avoid ambiguous locator errors
13. Add generous timeouts (5-10 seconds) for element visibility checks
14. If script gets stuck, it should gracefully continue instead of failing completely
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

            print(f"✓ Script written to {script_path}")
            print(f"Script length: {len(playwright_code)} characters, {len(playwright_code.splitlines())} lines")

            # Log first 50 lines of script for debugging
            script_lines = playwright_code.splitlines()
            print("\n" + "=" * 80)
            print("PLAYWRIGHT SCRIPT (first 50 lines):")
            print("=" * 80)
            for i, line in enumerate(script_lines[:50], 1):
                print(f"{i:3d}: {line}")
            if len(script_lines) > 50:
                print(f"... ({len(script_lines) - 50} more lines)")
            print("=" * 80 + "\n")

            # Execute the script
            print("Running Playwright script...")
            print(f"Command: python {script_path}")
            print(f"Working directory: {temp_dir}")
            print(f"Timeout: 300 seconds (5 minutes)")

            result = subprocess.run(
                ['python', script_path],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            print(f"\n{'=' * 80}")
            print(f"SCRIPT EXECUTION COMPLETED")
            print(f"{'=' * 80}")
            print(f"Return code: {result.returncode}")
            print(f"Stdout length: {len(result.stdout)} characters")
            print(f"Stderr length: {len(result.stderr)} characters")

            if result.stdout:
                print(f"\n{'=' * 80}")
                print(f"STDOUT:")
                print(f"{'=' * 80}")
                print(result.stdout)
                print(f"{'=' * 80}\n")
            else:
                print("⚠️  No stdout output")

            if result.stderr:
                print(f"\n{'=' * 80}")
                print(f"STDERR:")
                print(f"{'=' * 80}")
                print(result.stderr)
                print(f"{'=' * 80}\n")
            else:
                print("✓ No stderr output")

            if result.returncode != 0:
                raise Exception(f"Playwright script failed with return code {result.returncode}: {result.stderr}")

            # List all files in temp directory
            print(f"\n{'=' * 80}")
            print(f"FILES IN TEMP DIRECTORY:")
            print(f"{'=' * 80}")
            for root, dirs, files in os.walk(temp_dir):
                level = root.replace(temp_dir, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    file_path = os.path.join(root, file)
                    file_size = os.path.getsize(file_path)
                    print(f"{subindent}{file} ({file_size:,} bytes)")
            print(f"{'=' * 80}\n")

            # Check if video was created
            video_path = os.path.join(temp_dir, 'output.webm')
            if not os.path.exists(video_path):
                # Check for alternative video file names
                possible_names = ['output.webm', 'video.webm', 'recording.webm', 'demo.webm']
                found_video = None
                for name in possible_names:
                    alt_path = os.path.join(temp_dir, name)
                    if os.path.exists(alt_path):
                        found_video = alt_path
                        print(f"⚠️  Found video with alternative name: {name}")
                        video_path = alt_path
                        break

                if not found_video:
                    error_msg = "Video file 'output.webm' was not created by the script.\n"
                    error_msg += f"Temp directory contents: {os.listdir(temp_dir)}\n"
                    error_msg += f"Expected path: {video_path}\n"
                    error_msg += "Script may have failed silently or saved video with different name."
                    raise Exception(error_msg)
            else:
                video_size = os.path.getsize(video_path)
                print(f"✓ Video file found: {video_path} ({video_size:,} bytes)")

            # Note: Audio merging now happens in STEP 7 after voice synthesis
            # This step only uploads the silent video
            print("\n" + "-" * 80)
            print("Note: Audio will be added later in STEP 7")
            print("-" * 80)

            # Upload video to S3 (without audio for now)
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
        product_url = payload.get('product_url', 'Unknown URL') if isinstance(payload, dict) else 'Unknown URL'
        user_email = payload.get('email') if isinstance(payload, dict) else None

        if submission_id:
            # Check if this submission has already been processed by checking if JSON file exists
            s3_client = boto3.client('s3', region_name=REGION)
            json_key = f"{S3_STAGING_PREFIX}/{submission_id}/{submission_id}.json"

            try:
                s3_client.head_object(Bucket=S3_BUCKET, Key=json_key)
                # File exists, this submission has already been processed
                print("=" * 80)
                print("⚠️  DUPLICATE INVOCATION DETECTED")
                print("=" * 80)
                print(f"Submission {submission_id} has already been processed (JSON file exists)")
                print("Exiting to avoid duplicate work and duplicate emails")
                print("=" * 80)
                return {"response": "Duplicate invocation - already processed", "duplicate": True}
            except s3_client.exceptions.NoSuchKey:
                # File doesn't exist, this is the first invocation - continue processing
                print("✓ First invocation for this submission - proceeding with processing")
                pass
            except Exception as check_error:
                # If we can't check, proceed anyway to avoid blocking legitimate requests
                print(f"Warning: Could not check for duplicate: {check_error}")
                sentry_sdk.capture_exception(check_error)
                pass

            # Save payload to S3 (this marks the submission as being processed)
            s3_key = save_payload_to_s3(payload, submission_id)
            print(f"Payload saved to S3: {s3_key}")

            # Send email notification that processing has started
            if user_email:
                send_email_notification(
                    subject="Kirbuk: Demo Video Generation Started",
                    body=f"Demo video generation has started for {product_url}",
                    recipient_email=user_email,
                    submission_id=submission_id
                )
            else:
                print("Warning: No user email found in payload, skipping start notification email")
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

        # Get roast mode from payload
        roast_mode = payload.get('roast_mode', False)
        print(f"🎭 Roast Mode: {'ENABLED - Spicy commentary activated!' if roast_mode else 'Disabled - Professional tone'}")

        # Create agent without memory session manager to avoid throttling
        agent = Agent(
            model=MODEL_ID,
            system_prompt=get_exploration_system_prompt(roast_mode),
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

            # Generate and save Playwright script FIRST (before audio)
            print("\n" + "=" * 80)
            print("STEP 3: Generating Playwright script")
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
                    sentry_sdk.capture_exception(file_save_exc)

            # Execute the Playwright script and create SILENT video
            print("\n" + "=" * 80)
            print("STEP 4: Executing Playwright script to create video")
            print("=" * 80)
            video_duration = 120.0  # Default duration
            try:
                video_s3_key = execute_playwright_script(playwright_code, submission_id)
                print(f"✓ Video successfully created and uploaded to S3: {video_s3_key}")

                # Download video temporarily to measure duration
                print("→ Measuring video duration...")
                import tempfile
                s3_client = boto3.client('s3', region_name=REGION)
                with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_video:
                    s3_client.download_file(S3_BUCKET, video_s3_key, temp_video.name)
                    video_duration = get_video_duration(temp_video.name)
                    # Clean up temp file
                    os.unlink(temp_video.name)

            except Exception as video_error:
                print(f"✗ Error creating video: {video_error}")
                import traceback
                print(f"Video creation traceback: {traceback.format_exc()}")
                print("⚠️  Continuing with default 2-minute duration for audio generation")
                sentry_sdk.capture_exception(video_error)

            # NOW generate voice script based on ACTUAL video duration AND Playwright script
            print("\n" + "=" * 80)
            print(f"STEP 5: Generating SSML voice script (for {video_duration:.1f}s video, with Playwright sync)")
            print("=" * 80)
            voice_script = None
            try:
                voice_script = generate_voice_script(
                    response,
                    payload['product_url'],
                    video_duration,
                    roast_mode,
                    playwright_script=playwright_code  # Pass Playwright script for synchronization
                )
                print(f"✓ Voice script generated ({len(voice_script)} characters)")

                voice_script_s3_key = save_voice_script_to_s3(voice_script, submission_id)
                print(f"✓ Voice script saved to S3: {voice_script_s3_key}")

                # Synthesize voice using AWS Polly
                print("\n" + "=" * 80)
                print("STEP 6: Synthesizing voice with AWS Polly")
                print("=" * 80)
                try:
                    voice_audio_s3_key = synthesize_voice_with_polly(voice_script, submission_id)
                    print(f"✓ Voice audio synthesized and saved to S3: {voice_audio_s3_key}")

                    # STEP 7: Merge audio with video now that both exist
                    print("\n" + "=" * 80)
                    print("STEP 7: Merging audio with video and background music")
                    print("=" * 80)
                    try:
                        import tempfile
                        import random
                        import glob

                        with tempfile.TemporaryDirectory() as temp_dir:
                            s3_client = boto3.client('s3', region_name=REGION)

                            # Download video from S3
                            video_path = os.path.join(temp_dir, 'video.webm')
                            print(f"→ Downloading video from S3: {video_s3_key}")
                            s3_client.download_file(S3_BUCKET, video_s3_key, video_path)
                            print(f"✓ Video downloaded (size: {os.path.getsize(video_path)} bytes)")

                            # Download audio from S3
                            audio_path = os.path.join(temp_dir, 'voice.mp3')
                            print(f"→ Downloading audio from S3: {voice_audio_s3_key}")
                            s3_client.download_file(S3_BUCKET, voice_audio_s3_key, audio_path)
                            print(f"✓ Audio downloaded (size: {os.path.getsize(audio_path)} bytes)")

                            # Select random background music
                            music_dir = '/app/audio/bg_music'
                            music_files = glob.glob(os.path.join(music_dir, '*.mp3'))

                            merged_video_path = os.path.join(temp_dir, 'merged.webm')

                            if music_files:
                                # Randomly select a background music file
                                selected_music = random.choice(music_files)
                                music_name = os.path.basename(selected_music)
                                print(f"🎵 Selected background music: {music_name}")

                                # Merge video, voice, and background music
                                print(f"→ Merging video, voice, and background music with FFmpeg...")
                                merge_audio_video_with_music(
                                    video_path,
                                    audio_path,
                                    selected_music,
                                    merged_video_path,
                                    voice_volume=1.0,    # Voice at 100%
                                    music_volume=0.15    # Background music at 15%
                                )
                                print(f"✓ Video merged with voice and background music (size: {os.path.getsize(merged_video_path)} bytes)")
                            else:
                                # No background music available, merge without it
                                print(f"⚠️  No background music files found in {music_dir}")
                                print(f"→ Merging video and voice only...")
                                merge_audio_video_with_ffmpeg(video_path, audio_path, merged_video_path)
                                print(f"✓ Audio and video merged (size: {os.path.getsize(merged_video_path)} bytes)")

                            # Upload merged video back to S3 (overwrite the old one)
                            print(f"→ Uploading merged video to S3...")
                            video_s3_key = save_video_to_s3(merged_video_path, submission_id)
                            print(f"✓ Final video with audio uploaded to S3: {video_s3_key}")

                    except Exception as merge_error:
                        print(f"✗ Error merging audio with video: {merge_error}")
                        import traceback
                        print(f"Audio merge traceback: {traceback.format_exc()}")
                        print("⚠️  Video uploaded without audio")
                        sentry_sdk.capture_exception(merge_error)

                except Exception as polly_error:
                    print(f"✗ Error synthesizing voice with Polly: {polly_error}")
                    import traceback
                    print(f"Polly synthesis traceback: {traceback.format_exc()}")
                    print("⚠️  Video will be uploaded without audio")
                    sentry_sdk.capture_exception(polly_error)

            except Exception as voice_error:
                print(f"✗ Error generating voice script: {voice_error}")
                # Don't fail the entire job if voice script generation fails
                import traceback
                print(f"Voice script generation traceback: {traceback.format_exc()}")
                print("⚠️  Video will be uploaded without narration")
                sentry_sdk.capture_exception(voice_error)

        print("\n" + "=" * 80)
        print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"Submission ID: {submission_id}")
        print("=" * 80)

        # Send success email notification
        if submission_id and user_email:
            send_email_notification(
                subject="Kirbuk: Demo Video Generation Complete",
                body=f"Demo video has been successfully generated for {product_url}",
                recipient_email=user_email,
                submission_id=submission_id
            )

        return {"response": response}

    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ WORKFLOW FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        print("=" * 80)

        # Send failure email notification
        submission_id = payload.get('submission_id') if isinstance(payload, dict) else None
        product_url = payload.get('product_url', 'Unknown URL') if isinstance(payload, dict) else 'Unknown URL'
        user_email = payload.get('email') if isinstance(payload, dict) else None
        if submission_id and user_email:
            send_email_notification(
                subject="Kirbuk: Demo Video Generation Failed",
                body=f"Demo video generation failed for {product_url}\n\nError: {str(e)}",
                recipient_email=user_email,
                submission_id=submission_id
            )

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
