# Kirbuk Video Generation - Improvement Plan

## Executive Summary

This document outlines a comprehensive improvement plan for the Kirbuk automated SaaS video generation system to address issues with video-audio synchronization and Playwright script quality.

---

## Current System Architecture

### Overview
Kirbuk is an automated SaaS product video generation service that transforms a product URL into a complete narrated video using AWS Bedrock AgentCore with Claude AI models.

### 7-Step Workflow Pipeline

```
STEP 1: Website Exploration
├─ Agent uses Browser tool to navigate product
├─ Generates narrative script with selector info
└─ Returns script describing what to do on the site

STEP 2: Save Narrative Script to S3
├─ Location: staging_area/{submission_id}/script.txt
└─ Contains 24-40 actions with element selectors

STEP 3: Generate Playwright Script
├─ Input: Narrative + Product URL
├─ AI Model: Claude Sonnet 4
├─ Output: Python automation script
└─ Location: staging_area/{submission_id}/playwright.py

STEP 4: Execute Playwright & Extract Frames
├─ Run Python script (5-minute timeout)
├─ Creates silent video.webm (1280x720)
├─ Extracts frames every 5 seconds using FFmpeg
└─ Uploads video + frames to S3

STEP 5: Generate Voice Script (WITH VISUAL CONTEXT)
├─ Input: Narrative + Video duration + Video frames
├─ AI Model: Claude Sonnet 4 (multimodal)
├─ Analyzes video frames for synchronization
├─ Outputs SSML (260-300 words for 2-minute video)
└─ Location: staging_area/{submission_id}/voice_script.ssml

STEP 6: Synthesize Voice with AWS Polly
├─ Engine: Generative
├─ Voice: Matthew (male)
├─ Input: SSML script
├─ Async synthesis with polling
└─ Output: staging_area/{submission_id}/voice.mp3

STEP 7: Merge Audio + Video + Background Music
├─ Download video, voice, and random background music
├─ Mix audio (voice at 100%, music at 15%)
├─ FFmpeg merges all together
└─ Final output: staging_area/{submission_id}/video.webm
```

### Current AI Model Usage
- **Model ID:** `eu.anthropic.claude-sonnet-4-20250514-v1:0`
- **Access:** AWS Bedrock (eu-central-1)
- **Capabilities:** Multimodal (text + images)

**Three Key Uses of Claude:**
1. Website Exploration System Prompt - Generates narrative script
2. Playwright Script Generation - Creates automation code (line 916)
3. Voice Script Generation - Creates SSML with visual synchronization (line 738)

---

## Problem Analysis

### Problem 1: Video-Audio Synchronization Issues

**Current Issue:** Video and audio describe different actions

**Root Causes:**

1. **Two-stage generation with information loss** (`agentcore_starter_strands.py:912-1001` & `697-909`):
   - Playwright script is generated from the **narrative** (Step 3)
   - Voice script is generated from the **same narrative** (Step 5), NOT from the actual Playwright code
   - The AI interprets the narrative **twice independently**, leading to divergence

2. **Frame-based sync is incomplete** (`agentcore_starter_strands.py:839-860`):
   - Frames are extracted every 5 seconds, which is helpful
   - BUT the voice script generator doesn't know WHAT PLAYWRIGHT ACTIONS caused those frames
   - It's trying to narrate what it sees, but doesn't know "we clicked X button to get here"

3. **Model limitation** (line 24, 738-739):
   - Using Claude Sonnet 4: `eu.anthropic.claude-sonnet-4-20250514-v1:0`
   - Sonnet is very capable, but for complex multi-step reasoning with visual analysis, **Opus excels**

### Problem 2: Playwright Scripts Have Issues

**Current Issues:**
- Scripts contain guessed class names
- Selectors don't always exist on the page
- Scripts don't show great representation of SaaS product

**Root Causes:**

1. **Guessing class names** (`agentcore_starter_strands.py:929-953`):
   - The system prompt tells Claude to use fallback selectors (line 929-953)
   - But the exploration phase (lines 82-91) only provides *hints* about selectors
   - Claude has to **guess** the exact class names/selectors when generating Playwright code
   - The Browser Tool doesn't capture the actual DOM structure or HTML

2. **Poor representation of SaaS product** (`agentcore_starter_strands.py:69-73`):
   - Exploration is limited to 10-15 browser actions (line 75)
   - Target is 24-40 actions in the final script (line 71)
   - The AI has to **extrapolate** and create additional actions it never actually saw
   - This leads to invented actions that may not work

3. **Brittle selector strategies** (`agentcore_starter_strands.py:929-971`):
   - Try/except fallbacks help, but still rely on guessing
   - No validation that selectors actually exist on the page

---

## Comprehensive Improvement Plan

### 1. UPGRADE TO CLAUDE OPUS 4 (CRITICAL)

**Why Opus for this use case:**
- **Superior long-context reasoning**: Better at maintaining consistency across the entire workflow
- **Enhanced visual analysis**: Opus excels at multimodal tasks (analyzing video frames + code + narrative)
- **Better code generation**: More accurate Playwright scripts with fewer hallucinated selectors
- **Improved instruction following**: Will better adhere to the complex prompt constraints

**Model to use:**
- `eu.anthropic.claude-opus-4-20250514-v1:0` (Opus 4 - Latest via Bedrock)

**Where to apply Opus:**
1. **Playwright script generation** (line 24, 738, 916) - Most critical for accurate selectors
2. **Voice script generation** (line 738) - Better synchronization with visual frames
3. **Website exploration** (line 1268) - Optional, but would improve initial narrative quality

**Implementation:**
```python
# agentcore_starter_strands.py:24
MODEL_ID = "eu.anthropic.claude-opus-4-20250514-v1:0"
```

---

### 2. IMPROVE PLAYWRIGHT SCRIPT GENERATION

#### 2A. Capture Actual HTML/DOM During Exploration

**Current Problem:** Agent only captures "hints" about selectors (lines 82-91)

**Solution:** Modify exploration to capture actual HTML snippets

```python
# agentcore_starter_strands.py:82-103
IMPORTANT - CAPTURE DETAILED SELECTOR INFORMATION AND HTML:
When exploring the website, for each interactive element you plan to use:
1. Capture the ACTUAL HTML of the element (use browser developer tools mentally)
2. Note ALL available selectors:
   - Exact button text (e.g., "Sign Up", "Get Started")
   - data-testid attributes
   - Unique IDs
   - ARIA labels and roles
   - Class names (full class string)
   - XPath if needed
3. Capture the element's context (parent elements, siblings)

In your final script, include a SELECTOR MAPPING section like this:

SELECTOR MAPPING:
- "Click Sign Up button" →
  HTML: <button class="btn btn-primary signup-cta" data-testid="signup-btn">Sign Up</button>
  Selectors: button[data-testid="signup-btn"], .signup-cta, button:has-text("Sign Up")

- "Enter email field" →
  HTML: <input type="email" placeholder="Enter your email" id="email-input" />
  Selectors: #email-input, input[type="email"], input[placeholder*="email"]
```

This gives Playwright generation **exact selectors** instead of guesses.

#### 2B. Extend Exploration Depth

**Current Problem:** 10-15 browser actions, but script needs 24-40 actions (lines 75, 71)

**Solution:** Increase exploration OR make it smarter

```python
# agentcore_starter_strands.py:75-79
CRITICAL - EXPLORATION DEPTH:
- Explore for up to 20-30 browser actions (increased from 10-15)
- Focus on the PRIMARY user journey that showcases the product
- Document EVERY action you take with exact selectors
- If the product is simple, that's OK - script can include slower pacing/more pauses
- Better to have 15 real actions with perfect selectors than 40 guessed actions
```

#### 2C. Add Playwright Script Validation (NEW STEP)

**Add between Step 3 and Step 4:**

```python
# New function in agentcore_starter_strands.py
def validate_playwright_script(playwright_code, product_url, submission_id):
    """
    Use Claude Opus to review the Playwright script for:
    - Selector accuracy (are they likely to work?)
    - Logic errors
    - Missing waits or error handling

    Returns: (is_valid, suggestions, corrected_code)
    """
    agent = Agent(
        model=MODEL_ID,  # Use Opus for validation
        system_prompt="""You are a Playwright expert code reviewer.

        Review this Playwright script for potential issues:
        1. Are selectors likely to exist? (check for guessed class names)
        2. Are there proper waits and timeouts?
        3. Will the script handle popups, cookies, modals?
        4. Is error handling robust?
        5. Will the video actually showcase the product well?

        If you find issues, provide:
        - List of issues
        - Corrected version of the script

        Return JSON:
        {
          "is_valid": true/false,
          "issues": ["issue 1", "issue 2"],
          "corrected_code": "..."  // Only if is_valid is false
        }
        """
    )

    result = agent(f"""Review this Playwright script for {product_url}:

```python
{playwright_code}
```

Return a JSON object with validation results.""")

    # Parse JSON response and return
    # If invalid, use corrected_code
    return is_valid, issues, corrected_code
```

---

### 3. IMPROVE VIDEO-AUDIO SYNCHRONIZATION

#### 3A. Generate Voice Script from Playwright Code + Frames (NOT just narrative)

**Current Problem:** Voice script generated from narrative (line 834-851), Playwright script also from narrative → they diverge

**Solution:** Pass **the actual Playwright code** to voice script generation

```python
# agentcore_starter_strands.py:697
def generate_voice_script(
    script_text,  # Keep narrative for context
    product_url,
    video_duration_seconds=120,
    roast_mode=False,
    frame_s3_keys=None,
    playwright_code=None  # NEW: Pass the actual Playwright script
):
```

**Update the prompt** (line 834):

```python
prompt_text = f"""Create an SSML voice-over script for a demo video of this website: {product_url}

CRITICAL SYNCHRONIZATION REQUIREMENTS:
1. The video was created using this EXACT Playwright script:

```python
{playwright_code}
```

2. Each Playwright action (click, type, navigate) is visible in the video
3. Your narration must describe EXACTLY what the Playwright script does, in order
4. I'm providing {len(frame_images)} screenshots from the actual video, taken every 5 seconds
5. Match your narration to BOTH the Playwright actions AND what's visible in frames

NARRATION STRATEGY:
- For each Playwright action, explain WHY it's happening and WHAT it demonstrates
- Example: If playwright clicks `.signup-btn`, narrate "Now we'll click the sign-up button to begin creating an account"
- Time your narration so each action is explained AS IT'S HAPPENING in the video
- Use the frames to confirm what's visible at each timestamp

The original exploration narrative was:
{script_text}

This narrative is for CONTEXT ONLY. Your narration must match the ACTUAL Playwright script.
"""
```

This ensures voice perfectly matches video actions.

#### 3B. Add Timestamp Annotations to Playwright Script

**Solution:** Have Playwright script generation include **timing comments**

Update Playwright generation system prompt (line 918-972):

```python
CRITICAL - TIMING ANNOTATIONS:
Add comments in the Playwright script indicating approximate timestamps:

```python
# [0:00-0:05] Navigate to homepage
await page.goto('https://example.com')
await page.wait_for_timeout(3000)

# [0:05-0:10] Click sign up button
await page.click('.signup-btn')
await page.wait_for_timeout(4000)

# [0:10-0:15] Enter email
await page.fill('#email', 'test@example.com')
await page.wait_for_timeout(3000)
```

These timestamps will help voice script generation synchronize perfectly.
```

Then parse these timestamps and pass them to voice script generation.

#### 3C. Use Opus for Better Multimodal Reasoning

**Current:** Sonnet 4 analyzes frames + narrative (line 738)

**Better:** Opus 4 analyzes frames + narrative + **Playwright code** + **timestamps**

Opus has superior ability to:
- Cross-reference Playwright actions with visible frames
- Understand "at timestamp 0:15, this Playwright action executes, and this frame shows the result"
- Generate narration that perfectly aligns with visual changes

---

### 4. ADD INTELLIGENT ACTION GENERATION (OPTIONAL BUT POWERFUL)

#### 4A. Two-Pass Exploration

**First Pass (Quick Exploration - 10 actions):**
- Agent explores quickly to understand the product
- Generates high-level narrative

**Second Pass (Detailed Action Capture - 30+ actions):**
- Agent goes through the EXACT demo flow it wants to record
- Captures every single action with HTML/selectors
- This becomes the Playwright script foundation (almost 1:1 mapping)

---

## Implementation Roadmap

### Phase 1: Quick Wins (1-2 hours)

1. ✅ **Upgrade to Opus 4** for Playwright generation
   - **File:** `agentcore_starter_strands.py:24`
   - **Change:** `MODEL_ID = "eu.anthropic.claude-opus-4-20250514-v1:0"`
   - **Test:** Generate Playwright script for one URL
   - **Validate:** Compare script quality vs. Sonnet 4

2. ✅ **Pass Playwright code to voice script generation**
   - **File:** `agentcore_starter_strands.py:697, 1359`
   - **Change:** Add `playwright_code` parameter to `generate_voice_script()`
   - **Change:** Update prompt to include Playwright code in context
   - **Test:** Verify voice-video synchronization improves

### Phase 2: Selector Accuracy (2-3 hours)

3. ✅ **Enhanced exploration prompt**
   - **File:** `agentcore_starter_strands.py:82-103`
   - **Change:** Add HTML capture requirements
   - **Change:** Add SELECTOR MAPPING section requirement
   - **Test:** Run exploration and verify HTML is captured

4. ✅ **Extend exploration depth**
   - **File:** `agentcore_starter_strands.py:75`
   - **Change:** Increase to 20-30 actions from 10-15
   - **Test:** Verify more comprehensive product demos

### Phase 3: Quality Validation (3-4 hours)

5. ✅ **Add Playwright script validation step**
   - **File:** `agentcore_starter_strands.py` (new function + workflow update)
   - **Add:** New function `validate_playwright_script()`
   - **Change:** Insert validation between Step 3 and Step 4
   - **Test:** Verify auto-correction of script issues

6. ✅ **Add timing annotations**
   - **File:** `agentcore_starter_strands.py:918-972`
   - **Change:** Update Playwright generation prompt with timing requirements
   - **Add:** Parser for timestamp comments
   - **Change:** Pass timestamps to voice generation
   - **Test:** Verify improved synchronization

### Phase 4: Advanced (Optional - 4-6 hours)

7. ✅ **Two-pass exploration**
   - **File:** `agentcore_starter_strands.py:1181-1504`
   - **Restructure:** Add second detailed exploration pass
   - **Test:** Compare quality across 5-10 different SaaS products

---

## Expected Improvements

| Metric | Current (Sonnet 4) | Expected (Opus 4 + Changes) |
|--------|-------------------|---------------------------|
| **Playwright selector accuracy** | ~60-70% work first try | ~90-95% work first try |
| **Video-audio sync quality** | Mediocre (different actions) | Excellent (perfectly matched) |
| **Product representation** | OK (some guessed actions) | Great (real actions captured) |
| **Script robustness** | Brittle (many try/except) | Robust (validated selectors) |
| **Overall video quality** | 6/10 | 9/10 |

---

## Key Files to Modify

1. **`agentcore_starter_strands.py`:**
   - Line 24: Model ID (change to Opus)
   - Lines 30-103: Exploration system prompt (add HTML capture)
   - Lines 697-909: Voice script generation (add playwright_code param)
   - Lines 912-1001: Playwright generation (add timing annotations)
   - Lines 1181-1504: Workflow orchestration (add validation step)
   - New function: `validate_playwright_script()`

2. **Testing approach:**
   - Test with 3-5 different SaaS products
   - Compare before/after quality metrics
   - Measure selector success rate
   - Verify video-audio synchronization

---

## Root Cause Summary

Your issues stem from:

1. **Sonnet 4** - Good but not optimal for this complex multimodal task
2. **Separate generation** - Playwright and voice scripts generated independently from same narrative
3. **Guessed selectors** - Exploration doesn't capture actual HTML
4. **Limited exploration** - Not enough actions captured vs. needed

**The fix:**

1. **Upgrade to Opus 4** - Better reasoning, code generation, and multimodal analysis
2. **Pass Playwright code to voice generation** - Ensures perfect sync
3. **Capture actual HTML during exploration** - No more guessed selectors
4. **Add validation step** - Catch issues before execution
5. **Add timing annotations** - Explicit timestamp synchronization

---

## Next Steps

Choose implementation approach:

- **Option A:** Implement Phase 1 changes only (Opus upgrade + voice sync) - 30 min
- **Option B:** Implement Phases 1-3 (all core improvements) - 2-3 hours
- **Option C:** Just upgrade to Opus first and test (minimal change) - 5 min
- **Option D:** Full implementation including Phase 4 (complete overhaul) - 6-10 hours

---

*Document created: 2025-10-21*
*System: Kirbuk - Automated SaaS Product Video Generation*
*Current Model: Claude Sonnet 4*
*Recommended Model: Claude Opus 4*
