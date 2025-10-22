# End Slide Implementation Plan

## Objective
Add a branded end slide to videos showing:
- Website title
- One-sentence description
- Website URL
- Brown theme matching Kirbuk branding

## Implementation Steps

### 1. Generate End Slide Image (Python + Pillow)

Create a new function `generate_end_slide(title, description, url, output_path)`:

```python
from PIL import Image, ImageDraw, ImageFont

def generate_end_slide(title, description, url, output_path, width=1280, height=720):
    """Generate an end slide image with website details in brown theme"""

    # Kirbuk brown theme colors
    bg_color = "#8B4513"      # Brown background (matches website)
    text_color = "#FFF8DC"    # Cornsilk text (matches website)
    accent_color = "#D2691E"  # Chocolate accent

    # Create image
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Load fonts (need to include font files in Docker image)
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        desc_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        url_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    except:
        # Fallback to default font
        title_font = desc_font = url_font = ImageFont.load_default()

    # Calculate text positions (centered)
    # Title at 30% height
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    title_y = int(height * 0.30)

    # Description at 50% height
    desc_bbox = draw.textbbox((0, 0), description, font=desc_font)
    desc_width = desc_bbox[2] - desc_bbox[0]
    desc_x = (width - desc_width) // 2
    desc_y = int(height * 0.50)

    # URL at 65% height
    url_bbox = draw.textbbox((0, 0), url, font=url_font)
    url_width = url_bbox[2] - url_bbox[0]
    url_x = (width - url_width) // 2
    url_y = int(height * 0.65)

    # Draw text with slight shadow for depth
    shadow_offset = 3

    # Title (with shadow)
    draw.text((title_x + shadow_offset, title_y + shadow_offset), title, font=title_font, fill="#000000")
    draw.text((title_x, title_y), title, font=title_font, fill=text_color)

    # Description
    draw.text((desc_x, desc_y), description, font=desc_font, fill=text_color)

    # URL (with accent color and shadow)
    draw.text((url_x + shadow_offset, url_y + shadow_offset), url, font=url_font, fill="#000000")
    draw.text((url_x, url_y), url, font=url_font, fill=accent_color)

    # Optional: Add decorative elements
    # Draw horizontal lines above and below URL
    line_y_top = url_y - 20
    line_y_bottom = url_y + 60
    draw.rectangle([(width*0.2, line_y_top), (width*0.8, line_y_top + 2)], fill=accent_color)
    draw.rectangle([(width*0.2, line_y_bottom), (width*0.8, line_y_bottom + 2)], fill=accent_color)

    # Save image
    img.save(output_path, 'PNG')
    print(f"✓ End slide generated: {output_path}")

    return output_path
```

### 2. Append End Slide to Video (FFmpeg)

Create a new function `append_end_slide_to_video(video_path, slide_path, output_path, slide_duration=5)`:

```python
def append_end_slide_to_video(video_path, slide_path, output_path, slide_duration=5, fade_duration=1.0):
    """Append end slide to video with fade transition"""
    import subprocess

    print(f"Appending end slide to video...")
    print(f"Video: {video_path}")
    print(f"Slide: {slide_path}")
    print(f"Output: {output_path}")
    print(f"Slide duration: {slide_duration}s, Fade: {fade_duration}s")

    # FFmpeg command:
    # 1. Create a video segment from the static slide image
    # 2. Add fade-in effect to the slide
    # 3. Concatenate original video with slide segment

    cmd = [
        'ffmpeg',
        '-i', video_path,                                    # Input: original video
        '-loop', '1',                                        # Loop the image
        '-t', str(slide_duration),                           # Duration of slide
        '-i', slide_path,                                    # Input: end slide image
        '-filter_complex',
        # Scale slide to match video resolution
        f'[1:v]scale=1280:720,format=yuv420p,'
        # Add fade-in effect at the start
        f'fade=t=in:st=0:d={fade_duration}:alpha=0[slide];'
        # Concatenate video and slide
        f'[0:v][slide]concat=n=2:v=1:a=0[outv]',
        '-map', '[outv]',                                    # Map concatenated video
        '-map', '0:a?',                                      # Map audio from original (if exists)
        '-c:v', 'libvpx-vp9',                               # Video codec
        '-c:a', 'copy',                                      # Copy audio codec
        '-shortest',                                         # End when shortest stream ends
        '-y',                                                # Overwrite output
        output_path
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode != 0:
        print(f"FFmpeg stderr: {result.stderr}")
        raise Exception(f"FFmpeg failed with return code {result.returncode}")

    print(f"✓ End slide appended to video: {output_path}")
    return output_path
```

### 3. Integration Points in Main Code

**In `agentcore_starter_strands.py`, after Step 6 (video generation):**

Location: After merging audio/video with background music, before uploading final video to S3

```python
# After line ~1297 where merged video is created
# Add end slide generation and appending

print("\n" + "-" * 80)
print("STEP 6.3: Adding end slide")
print("-" * 80)

# Generate end slide
end_slide_path = os.path.join(temp_dir, 'end_slide.png')
generate_end_slide(
    title=product_title,           # Need to extract from payload or website
    description=product_description,  # Need to extract from payload or narrative
    url=payload['product_url'],
    output_path=end_slide_path
)

# Append end slide to merged video
final_video_path = os.path.join(temp_dir, 'final_with_end.webm')
append_end_slide_to_video(
    video_path=merged_video_path,
    slide_path=end_slide_path,
    output_path=final_video_path,
    slide_duration=5,    # 5 seconds
    fade_duration=1.0    # 1 second fade-in
)

# Use final_video_path for S3 upload instead of merged_video_path
```

### 4. Required Changes

#### A. Update Dockerfile
Add font packages to support text rendering:
```dockerfile
RUN apt-get update && apt-get install -y \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    && rm -rf /var/lib/apt/lists/*
```

#### B. Extract Website Title and Description
Two options:

**Option 1:** Extract from Browser tool output (Step 1)
- Parse the narrative script to find title/description
- Use Claude to extract structured data from narrative

**Option 2:** Add to form submission
- Add optional "Product Title" and "Product Description" fields to web form
- Pass through payload

**Recommended:** Hybrid approach:
- Use form fields if provided
- Otherwise, use Claude to extract from narrative script
```python
def extract_product_info(narrative_script, product_url):
    """Extract title and description from narrative using Claude"""
    agent = Agent(model=MODEL_ID)

    prompt = f"""Extract the website title and a one-sentence description from this narrative:

{narrative_script}

Return ONLY a JSON object with this exact format:
{{"title": "Website Title", "description": "One sentence description"}}

If the title or description cannot be determined, use the URL: {product_url}
"""

    result = agent(prompt)
    # Parse JSON response
    # Return title and description
```

#### C. Update Web Form (Optional Enhancement)
Add optional fields to index.html:
```html
<div class="form-group">
    <label for="product_title">Product Title (Optional)</label>
    <input type="text" id="product_title" name="product_title"
           placeholder="e.g., My Awesome SaaS Product">
    <p class="helper-text">Will be extracted from website if not provided</p>
</div>

<div class="form-group">
    <label for="product_description">One-line Description (Optional)</label>
    <input type="text" id="product_description" name="product_description"
           placeholder="e.g., The easiest way to manage your projects">
    <p class="helper-text">Brief description for the end slide</p>
</div>
```

### 5. Testing Considerations

1. **Text Length**: Handle long titles/descriptions with text wrapping or truncation
2. **Font Availability**: Ensure fonts are available in Docker container
3. **Video Length**: Ensure slide duration doesn't make video too long
4. **Audio Handling**: Fade out audio before slide or continue playing
5. **Performance**: Image generation and video concatenation add ~5-10 seconds processing time

### 6. Alternative: Simpler Approach

If FFmpeg concatenation proves complex, use overlay instead:

```python
# Overlay end slide on last N seconds of video
cmd = [
    'ffmpeg',
    '-i', video_path,
    '-loop', '1',
    '-i', slide_path,
    '-filter_complex',
    # Calculate start time: video_duration - slide_duration
    f'[1:v]fade=t=in:st=0:d=1:alpha=1[slide];'
    f'[0:v][slide]overlay=0:0:enable=\'gte(t,{video_duration - slide_duration})\'[outv]',
    '-map', '[outv]',
    '-map', '0:a',
    output_path
]
```

This overlays the slide on the last 5 seconds instead of appending, which is simpler but may obscure video content.

### 7. Implementation Order

1. **Phase 1**: Basic implementation
   - Add Pillow to requirements
   - Create `generate_end_slide()` function
   - Create `append_end_slide_to_video()` function
   - Update Dockerfile with fonts
   - Test locally

2. **Phase 2**: Integration
   - Add Claude-based title/description extraction
   - Integrate into Step 6 workflow
   - Handle edge cases (long text, missing fonts)

3. **Phase 3**: Enhancement (optional)
   - Add form fields for title/description
   - Add audio fade-out before slide
   - Customize slide design per brand

### 8. Estimated Effort

- **Code changes**: 2-3 hours
- **Testing**: 1-2 hours
- **Deployment**: 30 minutes
- **Total**: ~4-6 hours

### 9. Potential Issues

1. **Font rendering**: May need to bundle custom fonts
2. **Text overflow**: Long URLs or titles need handling
3. **Video encoding**: Re-encoding video adds processing time
4. **Audio sync**: Need to ensure audio doesn't cut off abruptly

### 10. Future Enhancements

- Animated transitions (zoom, pan)
- Add company logo to end slide
- Customizable themes per customer
- Call-to-action button visual
- QR code generation for URL
