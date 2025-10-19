# Research: Adding Intro/Outro Slides with Fade Effects

**Date:** 2025-10-19
**Status:** Research Only - Not Implemented

## Executive Summary

Adding intro/outro slides with fade effects is **LOW-MEDIUM COMPLEXITY** (4/10) and can be implemented using either:
1. **FFmpeg post-processing** (Recommended - simpler, more reliable)
2. **Playwright HTML slides** (More flexible but trickier)

Estimated implementation time: 4-6 hours

## Requirements Analysis

### Desired Features
- **Intro Slide**: Show URL, branding, colors before video starts
- **Outro Slide**: Show URL, call-to-action after video ends
- **Fade Effects**: Smooth fade in/out transitions between slides and content
- **Automatic Generation**: No manual video editing required

### Design Considerations
- Slide duration (2-3 seconds typical)
- Text content (URL, tagline, branding)
- Visual design (colors, gradients, logos)
- Fade timing (0.5-1 second transitions)

## Technical Approaches

### Approach 1: FFmpeg Post-Processing (RECOMMENDED)

Generate intro/outro images with Python, then use FFmpeg to combine with video.

#### Implementation Steps

**1. Generate Intro/Outro Images (Python + Pillow)**

```python
from PIL import Image, ImageDraw, ImageFont

def create_intro_slide(product_url, output_path, width=1920, height=1080):
    """Create an intro slide with gradient background and text"""

    # Create image with gradient background
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)

    # Draw gradient background
    for y in range(height):
        # Interpolate between two colors
        r = int(30 + (60 - 30) * y / height)    # Dark blue to lighter blue
        g = int(60 + (100 - 60) * y / height)
        b = int(120 + (180 - 120) * y / height)
        draw.rectangle([(0, y), (width, y+1)], fill=(r, g, b))

    # Load fonts
    try:
        title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 80)
        url_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 60)
    except:
        title_font = ImageFont.load_default()
        url_font = ImageFont.load_default()

    # Draw title text
    title = "Product Demo"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    title_y = height // 3

    # Draw text with shadow for better readability
    shadow_offset = 3
    draw.text((title_x + shadow_offset, title_y + shadow_offset), title,
              fill=(0, 0, 0, 128), font=title_font)
    draw.text((title_x, title_y), title, fill=(255, 255, 255), font=title_font)

    # Draw URL
    url_bbox = draw.textbbox((0, 0), product_url, font=url_font)
    url_width = url_bbox[2] - url_bbox[0]
    url_x = (width - url_width) // 2
    url_y = height // 2

    draw.text((url_x + shadow_offset, url_y + shadow_offset), product_url,
              fill=(0, 0, 0, 128), font=url_font)
    draw.text((url_x, url_y), product_url, fill=(255, 255, 255), font=url_font)

    # Save image
    img.save(output_path)
    print(f"✓ Intro slide created: {output_path}")
    return output_path

def create_outro_slide(product_url, output_path, width=1920, height=1080):
    """Create an outro slide with call-to-action"""

    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)

    # Different gradient for outro
    for y in range(height):
        r = int(20 + (40 - 20) * y / height)
        g = int(40 + (80 - 40) * y / height)
        b = int(80 + (140 - 80) * y / height)
        draw.rectangle([(0, y), (width, y+1)], fill=(r, g, b))

    try:
        title_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 70)
        url_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 60)
    except:
        title_font = ImageFont.load_default()
        url_font = ImageFont.load_default()

    # Draw "Visit" text
    title = "Visit Us"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    title_y = height // 3

    shadow_offset = 3
    draw.text((title_x + shadow_offset, title_y + shadow_offset), title,
              fill=(0, 0, 0, 128), font=title_font)
    draw.text((title_x, title_y), title, fill=(255, 255, 255), font=title_font)

    # Draw URL
    url_bbox = draw.textbbox((0, 0), product_url, font=url_font)
    url_width = url_bbox[2] - url_bbox[0]
    url_x = (width - url_width) // 2
    url_y = height // 2

    draw.text((url_x + shadow_offset, url_y + shadow_offset), product_url,
              fill=(0, 0, 0, 128), font=url_font)
    draw.text((url_x, url_y), product_url, fill=(255, 255, 255), font=url_font)

    img.save(output_path)
    print(f"✓ Outro slide created: {output_path}")
    return output_path
```

**2. Combine with FFmpeg**

```python
def add_intro_outro_with_fades(input_video, intro_image, outro_image, output_video):
    """
    Add intro and outro slides with fade transitions using FFmpeg

    Timeline:
    - Intro slide: 0-3s (fade in 0-0.5s, hold 0.5-2.5s, fade out 2.5-3s)
    - Main video: 3s-end (fade in from intro)
    - Outro slide: after video (fade in from video, hold, fade out)
    """
    import subprocess

    # Step 1: Convert intro image to 3-second video with fades
    intro_duration = 3.0
    fade_duration = 0.5

    intro_video = '/tmp/intro.webm'
    cmd_intro = [
        'ffmpeg',
        '-loop', '1',
        '-i', intro_image,
        '-t', str(intro_duration),
        '-vf', f'fade=t=in:st=0:d={fade_duration},fade=t=out:st={intro_duration-fade_duration}:d={fade_duration}',
        '-c:v', 'libvpx-vp9',
        '-pix_fmt', 'yuva420p',
        '-r', '30',
        intro_video
    ]

    subprocess.run(cmd_intro, check=True)
    print(f"✓ Intro video created with fades")

    # Step 2: Convert outro image to 3-second video with fades
    outro_video = '/tmp/outro.webm'
    cmd_outro = [
        'ffmpeg',
        '-loop', '1',
        '-i', outro_image,
        '-t', str(intro_duration),
        '-vf', f'fade=t=in:st=0:d={fade_duration},fade=t=out:st={intro_duration-fade_duration}:d={fade_duration}',
        '-c:v', 'libvpx-vp9',
        '-pix_fmt', 'yuva420p',
        '-r', '30',
        outro_video
    ]

    subprocess.run(cmd_outro, check=True)
    print(f"✓ Outro video created with fades")

    # Step 3: Add fade in to main video
    main_with_fade = '/tmp/main_fade.webm'
    cmd_main_fade = [
        'ffmpeg',
        '-i', input_video,
        '-vf', f'fade=t=in:st=0:d={fade_duration}',
        '-c:v', 'libvpx-vp9',
        '-c:a', 'copy',
        main_with_fade
    ]

    subprocess.run(cmd_main_fade, check=True)
    print(f"✓ Main video fade applied")

    # Step 4: Concatenate all three videos with crossfade
    # Create concat list
    concat_file = '/tmp/concat_list.txt'
    with open(concat_file, 'w') as f:
        f.write(f"file '{intro_video}'\n")
        f.write(f"file '{main_with_fade}'\n")
        f.write(f"file '{outro_video}'\n")

    cmd_concat = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file,
        '-c:v', 'libvpx-vp9',
        '-c:a', 'libopus',
        output_video
    ]

    subprocess.run(cmd_concat, check=True)
    print(f"✓ Final video with intro/outro created: {output_video}")

    # Cleanup temp files
    import os
    os.remove(intro_video)
    os.remove(outro_video)
    os.remove(main_with_fade)
    os.remove(concat_file)

    return output_video
```

**3. Integration with Current Workflow**

```python
# In agentcore_starter_strands.py, after STEP 7 (audio merge)

# STEP 8: Add intro/outro slides
print("\n" + "=" * 80)
print("STEP 8: Adding intro and outro slides with fade effects")
print("=" * 80)

try:
    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate intro/outro images
        intro_image = os.path.join(temp_dir, 'intro.png')
        outro_image = os.path.join(temp_dir, 'outro.png')

        create_intro_slide(product_url, intro_image)
        create_outro_slide(product_url, outro_image)

        # Download current video from S3
        current_video = os.path.join(temp_dir, 'current.webm')
        s3_client.download_file(S3_BUCKET, video_s3_key, current_video)

        # Add intro/outro
        final_video = os.path.join(temp_dir, 'final.webm')
        add_intro_outro_with_fades(current_video, intro_image, outro_image, final_video)

        # Upload final video back to S3
        video_s3_key = save_video_to_s3(final_video, submission_id)
        print(f"✓ Final video with intro/outro uploaded: {video_s3_key}")

except Exception as intro_outro_error:
    print(f"⚠️  Error adding intro/outro slides: {intro_outro_error}")
    sentry_sdk.capture_exception(intro_outro_error)
    print("Continuing with video without intro/outro")
```

#### Pros & Cons

**Pros:**
- ✅ Clean separation of concerns (video recording vs post-processing)
- ✅ Reliable - FFmpeg is battle-tested for video manipulation
- ✅ Flexible - Easy to customize slide design
- ✅ No impact on Playwright recording
- ✅ Can add slides even if Playwright script changes

**Cons:**
- ⚠️ Adds processing time (~5-10 seconds)
- ⚠️ Requires FFmpeg filters knowledge
- ⚠️ More complex pipeline (more failure points)

---

### Approach 2: Playwright HTML Slides

Record intro/outro slides directly in Playwright by navigating to HTML pages.

#### Implementation Steps

**1. Generate HTML Slide Pages**

```python
def create_intro_html(product_url, output_path):
    """Create HTML file for intro slide"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                margin: 0;
                padding: 0;
                height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                font-family: Arial, sans-serif;
                animation: fadeIn 0.5s ease-in;
            }}

            @keyframes fadeIn {{
                from {{ opacity: 0; }}
                to {{ opacity: 1; }}
            }}

            @keyframes fadeOut {{
                from {{ opacity: 1; }}
                to {{ opacity: 0; }}
            }}

            .fade-out {{
                animation: fadeOut 0.5s ease-out forwards;
            }}

            h1 {{
                color: white;
                font-size: 72px;
                margin: 20px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            }}

            .url {{
                color: #e0e0e0;
                font-size: 48px;
                margin: 20px;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
            }}
        </style>
        <script>
            // Fade out after 2.5 seconds
            setTimeout(() => {{
                document.body.classList.add('fade-out');
            }}, 2500);
        </script>
    </head>
    <body>
        <h1>Product Demo</h1>
        <div class="url">{product_url}</div>
    </body>
    </html>
    """

    with open(output_path, 'w') as f:
        f.write(html)

    return output_path

def create_outro_html(product_url, output_path):
    """Create HTML file for outro slide"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                margin: 0;
                padding: 0;
                height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                background: linear-gradient(135deg, #141e30 0%, #243b55 100%);
                font-family: Arial, sans-serif;
                animation: fadeIn 0.5s ease-in;
            }}

            @keyframes fadeIn {{
                from {{ opacity: 0; }}
                to {{ opacity: 1; }}
            }}

            h1 {{
                color: white;
                font-size: 64px;
                margin: 20px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            }}

            .url {{
                color: #4da8ff;
                font-size: 48px;
                margin: 20px;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
            }}
        </style>
    </head>
    <body>
        <h1>Visit Us</h1>
        <div class="url">{product_url}</div>
    </body>
    </html>
    """

    with open(output_path, 'w') as f:
        f.write(html)

    return output_path
```

**2. Modify Playwright Script Generation Prompt**

```python
# In generate_playwright_script() system prompt, add:

"""
INTRO AND OUTRO SLIDES:
Before the main demo, navigate to 'intro.html' and wait 3 seconds to record the intro slide.
After the main demo, navigate to 'outro.html' and wait 3 seconds to record the outro slide.

Example structure:
1. Navigate to intro.html, wait 3000ms
2. Navigate to main website, perform demo
3. Navigate to outro.html, wait 3000ms
"""
```

**3. Inject HTML Files into Playwright Execution**

```python
# In execute_playwright_script(), before running the script:

# Create intro/outro HTML files
intro_html = os.path.join(temp_dir, 'intro.html')
outro_html = os.path.join(temp_dir, 'outro.html')

create_intro_html(product_url, intro_html)
create_outro_html(product_url, outro_html)

print(f"✓ Intro HTML created: {intro_html}")
print(f"✓ Outro HTML created: {outro_html}")

# Then execute Playwright script as normal
```

#### Pros & Cons

**Pros:**
- ✅ Single video recording (no post-processing)
- ✅ CSS animations for smooth fades
- ✅ Faster overall (no FFmpeg processing)
- ✅ Easier to add interactive elements if needed

**Cons:**
- ⚠️ Relies on LLM generating correct navigation code
- ⚠️ HTML/CSS timing can be unreliable
- ⚠️ Harder to customize without regenerating video
- ⚠️ Fade timing depends on Playwright's page loading

---

## Complexity Assessment

### Approach 1 (FFmpeg): **MEDIUM** (5/10)

| Component | Complexity | Time Estimate |
|-----------|-----------|---------------|
| Image generation (Pillow) | Low (2/10) | 1 hour |
| FFmpeg fade commands | Medium (5/10) | 2 hours |
| Video concatenation | Medium (6/10) | 1-2 hours |
| Integration & testing | Medium (5/10) | 1 hour |
| **TOTAL** | **Medium (5/10)** | **5-6 hours** |

### Approach 2 (Playwright): **LOW-MEDIUM** (4/10)

| Component | Complexity | Time Estimate |
|-----------|-----------|---------------|
| HTML/CSS slides | Low (2/10) | 1 hour |
| Prompt modifications | Low (3/10) | 1 hour |
| File injection | Low (2/10) | 30 min |
| Testing & iteration | Medium (5/10) | 1-2 hours |
| **TOTAL** | **Low-Medium (4/10)** | **3.5-4.5 hours** |

---

## Expected Quality

### Visual Quality: **8/10**

Both approaches can produce professional-looking slides:
- Clean gradient backgrounds
- Readable text with shadows
- Smooth fade transitions
- Brand-consistent colors

### Reliability:

**Approach 1 (FFmpeg): 9/10** - Very reliable
- FFmpeg is battle-tested
- Deterministic output
- Easy to debug

**Approach 2 (Playwright): 7/10** - Good but variable
- Depends on LLM following instructions
- CSS animations can have timing issues
- May need multiple attempts to get right

---

## Cost Analysis

### Approach 1 (FFmpeg)
- **Processing Time**: +5-10 seconds per video
- **LLM Cost**: $0 (no additional prompts)
- **Storage**: +2 MB for temp files (negligible)
- **Total Added Cost**: ~$0.001 (compute time)

### Approach 2 (Playwright)
- **Processing Time**: +6 seconds (3s intro + 3s outro)
- **LLM Cost**: Minimal (slightly longer prompt)
- **Storage**: Negligible
- **Total Added Cost**: ~$0.002 (longer recording)

---

## Design Variations

### Basic Design (Recommended for MVP)
- Solid gradient background
- Product URL centered
- Simple "Demo" title
- 0.5s fade in/out

### Enhanced Design (Future)
- Logo overlay
- Custom brand colors
- Animated text entrance
- Progress indicator
- QR code for mobile

### Premium Design (Advanced)
- Video background
- Particle effects
- Custom fonts
- Music/sound effects
- Multiple language support

---

## Implementation Recommendation

### **Recommended: Approach 1 (FFmpeg Post-Processing)**

**Why:**
1. **More Reliable**: FFmpeg is deterministic and well-tested
2. **Better Separation**: Keep Playwright focused on web recording
3. **Easier Debugging**: Can test slides independently
4. **More Flexible**: Easy to update slide design without regenerating video
5. **Professional Quality**: FFmpeg filters produce smooth, high-quality transitions

### Implementation Plan

**Phase 1: Basic Slides (2-3 hours)**
1. Add Pillow image generation functions
2. Create basic gradient backgrounds
3. Add text with shadows
4. Test image output

**Phase 2: FFmpeg Integration (2-3 hours)**
1. Add fade filters to images
2. Implement video concatenation
3. Test with sample videos
4. Add error handling

**Phase 3: Integration (1 hour)**
1. Add STEP 8 to agent workflow
2. Update S3 upload to use final video
3. Add Sentry tracking
4. Deploy and test

---

## Alternative: Optional Feature

Make intro/outro slides **optional** via checkbox:

```python
# In payload
add_intro_outro = payload.get('add_intro_outro', False)

if add_intro_outro:
    # STEP 8: Add slides
    ...
else:
    print("⏭️  Skipping intro/outro slides (not requested)")
```

This allows:
- Users who want plain videos can opt out
- A/B testing to measure impact
- Gradual rollout of feature

---

## Conclusion

### Complexity: **LOW-MEDIUM** (4-5/10)
- Straightforward image generation with Pillow
- Well-documented FFmpeg commands
- Clear integration point (after audio merge)
- 5-6 hours of development

### Expected Quality: **HIGH** (8/10)
- Professional-looking slides
- Smooth fade transitions
- Reliable FFmpeg processing
- Customizable designs

### ROI: **MEDIUM-HIGH**
- **User Value**: More polished, professional videos
- **Branding**: Consistent intro/outro reinforces product
- **Cost**: Minimal (~$0.001 per video)
- **Differentiation**: Nice-to-have feature

### Recommendation: **IMPLEMENT (Lower Priority)**
This is a nice enhancement that improves video polish and professionalism. However, it's lower priority than core functionality (feedback/regeneration, fixing bugs). Implement after:
1. Current bugs resolved
2. Video generation is reliable
3. Feedback/regeneration feature (if doing)

**Suggested Timeline:** After 2-3 weeks, when core features are stable
