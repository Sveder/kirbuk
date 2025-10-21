# Prompt for Claude Opus: Kirbuk Video Generation System Improvements

## Context

I'm working on Kirbuk, an automated SaaS product video generation system. The system takes a product URL and generates a complete narrated demo video automatically.

## Current Architecture

### Technology Stack
- **AI Model:** Claude Sonnet 4 (`eu.anthropic.claude-sonnet-4-20250514-v1:0`) via AWS Bedrock
- **Browser Automation:** Playwright (Python) for recording demos
- **Voice Synthesis:** AWS Polly Generative engine (Matthew voice)
- **Video Processing:** FFmpeg for frame extraction and audio merging
- **Agent Framework:** AWS Bedrock AgentCore with Strands

### 7-Step Workflow

1. **Website Exploration (Claude Sonnet 4 + Browser Tool)**
   - Agent explores the SaaS product website (10-15 browser actions max)
   - Generates narrative script describing what to do (targets 24-40 actions for ~2 min video)
   - Captures hints about selectors (button text, placeholders, ARIA labels, class names)

2. **Save Narrative Script to S3**
   - Stores the exploration narrative as `script.txt`

3. **Generate Playwright Script (Claude Sonnet 4)**
   - INPUT: Narrative script + Product URL
   - OUTPUT: Python Playwright automation script
   - Script must record 1280x720 WebM video, save as `output.webm`
   - Uses fallback selector strategies (text → role → class → generic)
   - Includes waits between actions (3-5 seconds each)

4. **Execute Playwright Script**
   - Runs the generated Python script (5-min timeout)
   - Creates SILENT video (no audio yet)
   - Extracts frames every 5 seconds using FFmpeg
   - Uploads video + frames to S3

5. **Generate Voice Script (Claude Sonnet 4 - Multimodal)**
   - INPUT: Original narrative + Video duration + Video frames (every 5s)
   - OUTPUT: SSML voice script (130-150 words/min, timed to video duration)
   - Analyzes video frames to synchronize narration with visuals
   - Removes unsupported SSML tags for Polly Generative engine

6. **Synthesize Voice (AWS Polly)**
   - Converts SSML to MP3 audio
   - Engine: Generative, Voice: Matthew

7. **Merge Audio + Video + Background Music (FFmpeg)**
   - Voice at 100%, background music at 15%
   - Final output: WebM with audio

## Current Problems

### Problem 1: Video and Audio Are Not Synced About the Same Actions

**Symptoms:**
- Voice narration describes different actions than what's happening in the video
- Timing feels off - narration doesn't match what's visible on screen

**My Hypothesis:**
- Playwright script generated from narrative (Step 3)
- Voice script ALSO generated from narrative (Step 5)
- Both interpret the same narrative independently → divergence
- Voice script sees frames but doesn't know WHAT PLAYWRIGHT ACTIONS caused those frames

### Problem 2: Playwright Scripts Have Issues

**Symptoms:**
- Scripts sometimes guess class names that don't exist
- Selectors fail at runtime
- Scripts don't always show a great representation of the SaaS product

**My Hypothesis:**
- Exploration phase (10-15 actions) captures less than needed (24-40 actions in final script)
- AI must extrapolate and invent actions it never actually saw
- Exploration only captures "hints" about selectors, not actual HTML
- No validation step before execution

## What I'm Using Claude Sonnet 4 For

1. **Website Exploration:** Browse and understand the product
2. **Playwright Script Generation:** Create automation code from narrative
3. **Voice Script Generation:** Create SSML with visual synchronization (multimodal - sees frames)

## Key Code References

- **File:** `kirbuk_agent/agentcore_starter_strands.py` (1508 lines)
- **Line 24:** Model ID definition (`MODEL_ID = "eu.anthropic.claude-sonnet-4-20250514-v1:0"`)
- **Lines 30-103:** Website exploration system prompt
- **Lines 82-91:** Selector capture instructions (hints only, not full HTML)
- **Line 75:** Exploration limit (10-15 actions)
- **Line 71:** Target actions for final video (24-40 actions)
- **Lines 697-909:** Voice script generation function
- **Lines 834-860:** Voice generation prompt (includes frames + narrative)
- **Lines 912-1001:** Playwright script generation function
- **Lines 929-953:** Robust selector strategy instructions (fallbacks)
- **Lines 1181-1504:** Main workflow orchestration (`invoke()` function)

## Questions for Claude Opus

1. **What are the root causes of the video-audio synchronization issues?**
   - Is my hypothesis correct that generating both scripts independently from the narrative causes divergence?
   - Should I pass the actual Playwright code to voice script generation?

2. **How can I improve Playwright script quality?**
   - Should exploration capture actual HTML/DOM instead of just "hints"?
   - Should I increase exploration depth to 20-30 actions?
   - Would a validation step help (Claude reviews script before execution)?

3. **Would upgrading to Claude Opus 4 help these issues?**
   - Where would Opus provide the most value? (exploration, Playwright generation, voice generation, all three?)
   - Opus is more expensive - is it worth it for this use case?

4. **Are there architectural improvements I'm missing?**
   - Should I use a two-pass exploration (quick overview + detailed action capture)?
   - Should Playwright scripts include timestamp annotations for better sync?
   - Any other strategies to improve quality?

5. **What's the highest-impact change I should make first?**
   - If I only have time for one improvement, what should it be?

## Constraints

- Must use AWS Bedrock (not direct Anthropic API)
- Playwright scripts must be generated (can't use manual scripts)
- Videos must be ~2 minutes long
- System must work autonomously without human intervention
- Already extracting frames every 5 seconds for visual context

## What I'm Looking For

Detailed technical recommendations on:
1. Root cause analysis (validate or correct my hypotheses)
2. Specific architectural improvements with rationale
3. Prompt engineering improvements for better results
4. Whether to upgrade to Opus 4 and where to use it
5. Priority order for implementing changes

Please provide concrete, actionable suggestions with technical depth. I'm a software engineer and can implement complex solutions.
