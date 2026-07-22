#!/usr/bin/env python3
"""
Meeting Video Processor - Knowledge Architect
Processes meeting videos with Gemini 3 Pro to extract comprehensive insights.

Supports large video files (1-2GB+) with:
- Resumable uploads for files >100MB
- Extended timeouts for processing
- Progress tracking during upload
- Retry logic with exponential backoff

Uses multi-stage analysis to extract:
- Full transcript
- Meeting summary
- Decisions (explicit and implicit)
- Ideas and project sparks
- Action items
- Frameworks and philosophies
- Status updates
- Blockers

Usage:
    python process_meeting.py <video_path> [output_directory]

    If output_directory is not specified, outputs are written to the same
    directory as the video file.
"""

import google.generativeai as genai
import os
import sys
import time
import socket
import argparse
from datetime import datetime
from pathlib import Path

# ============================================================================
# Configuration Constants
# ============================================================================

# Large file handling constants
MAX_UPLOAD_TIMEOUT = 1800  # 30 minutes for 2GB uploads
PROCESSING_POLL_INTERVAL_START = 30  # seconds
PROCESSING_POLL_INTERVAL_MAX = 120  # seconds
API_CALL_TIMEOUT = 1200  # 20 minutes per extraction
MAX_RETRIES = 3
RETRY_DELAY_BASE = 30  # seconds

# Model to use - Gemini 3.x Pro multimodal (gemini-3-pro-preview was retired by
# Google ~2026-06; generateContent returns 404 even though it still lists).
MODEL_NAME = "gemini-3.1-pro-preview"

# Raise the per-call output ceiling so long extractions are not truncated.
# Current Gemini 2.5/3.x Pro models support up to 65536 output tokens.
MAX_OUTPUT_TOKENS = 32768

# Single-pass verbatim transcription of long recordings stops early (the model
# truncates well before the end). Transcribe in contiguous time windows of this
# length and concatenate to force full coverage. Requires ffprobe for duration;
# falls back to a single pass if duration cannot be determined.
TRANSCRIPT_CHUNK_MINUTES = 10

# Audio-first preprocessing. Long VIDEOS fail two ways: the Gemini File API hard-
# rejects files over 2 GiB, and on long recordings the windowed video transcription
# mis-parses duration (e.g. reads 1:09:16 as 9:16), blanks windows, repeats passages,
# and scrambles speakers. The audio track alone avoids both: it is tiny, uploads in
# seconds, and gives correct per-window timestamps. For video inputs at or above
# either threshold below, the script extracts the audio stream and processes that.
# (Trade-off: on-screen slide visuals are not seen; speech and insights are intact.)
AUDIO_FIRST_DURATION_SECONDS = 50 * 60      # ~50 minutes
AUDIO_FIRST_SIZE_BYTES = int(1.8 * 1024 ** 3)  # 1.8 GiB (safe margin under the 2 GiB cap)
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}

# ============================================================================
# Prompts for Multi-Stage Analysis
# ============================================================================

TRANSCRIPT_PROMPT = """
You are a professional transcriptionist. Create a COMPLETE verbatim transcript of this meeting video.

Requirements:
1. Include ALL spoken content - do not skip or summarize
2. Add timestamps in [HH:MM:SS] format at regular intervals (every 30-60 seconds of speaking)
3. Identify speakers where possible (Speaker 1, Speaker 2, or names if mentioned)
4. Include verbal fillers, false starts, and corrections to preserve authenticity
5. Note any non-verbal audio cues in brackets [laughs], [pause], [crosstalk]
6. If audio is unclear, mark as [inaudible] or [unclear]

Format:
[00:00:00] Speaker: Text of what they said...

This must be the FULL transcript, not a summary. Every word matters.
"""

TRANSCRIPT_CHUNK_PROMPT = """
You are a professional transcriptionist. Create a COMPLETE verbatim transcript of
ONLY the portion of this meeting video between {start} and {end}.

Requirements:
1. Transcribe EVERY word spoken within the {start} to {end} window - do not skip or summarize
2. Do NOT transcribe anything before {start} or after {end}
3. Add timestamps in [HH:MM:SS] format every 30-60 seconds of speaking
4. Identify speakers where possible (names if mentioned, else Speaker 1 / Speaker 2)
5. Preserve verbal fillers, false starts, and corrections to keep authenticity
6. Note non-verbal audio cues in brackets: [laughs], [pause], [crosstalk]
7. Mark unclear audio as [inaudible] or [unclear]
8. Begin at the first utterance at or after {start} and continue through {end}

Format:
[HH:MM:SS] Speaker: Text of what they said...

This is a PARTIAL transcript covering only {start} to {end}. Transcribe the entire
window and do not stop early. Every word matters.
"""

SUMMARY_PROMPT = """
You are the knowledge architect for this meeting. Create a comprehensive meeting summary.

Based on the video, provide:

# Meeting Summary

## Overview
- Date/Time context
- Participants (names/roles if identifiable)
- Meeting purpose/context

## Key Discussion Points
For each major topic discussed:
- What was discussed
- Key points raised
- Outcomes/conclusions

## Critical Insights
- Most important takeaways
- Strategic observations
- Notable quotes or statements

## Open Questions
- Unresolved items
- Topics needing follow-up

This summary should be substantial - for an hour+ meeting, expect 2-4 pages of content.
Be thorough. Missing content is unacceptable.
"""

DECISIONS_PROMPT = """
You are mining this meeting for ALL decisions - both explicit and implicit.

Extract every decision into these categories:

# Decisions Made

## Explicit Decisions
Decisions that were clearly stated:
- "[Timestamp] Decision: [what was decided]"
- Include context and rationale if discussed

## Implicit Decisions
Decisions made by NOT deciding or by assumption:
- Things deprioritized ("let's not wait for...")
- Defaults accepted without discussion
- Directions taken by omission

## Deferred Decisions
Items explicitly pushed to later:
- What was deferred
- Why it was deferred
- When it might be revisited

## Decision Rationale
For major decisions, capture the reasoning discussed.

Look for phrases like:
- "Let's go with..."
- "We've decided..."
- "The plan is to..."
- "We're not going to..."
- "For now, let's..."
"""

IDEAS_PROMPT = """
You are hunting for ALL ideas mentioned in this meeting - even casual ones.

Extract into these categories:

# Ideas & Project Sparks

## Feature Ideas
Ideas for features in existing projects:
- [Timestamp] "Description of the idea"
- Context: where/why it came up
- Related project if mentioned

Look for:
- "Wouldn't it be cool if..."
- "We could also..."
- "What if we..."
- "It would be nice to..."

## Project Sparks
New tool concepts, standalone initiatives:
- Completely new projects mentioned
- Tools that could be built
- Services or systems proposed

## Embedded Ideas
Ideas hidden in problem discussions:
- "The issue is we don't have X" → X is an idea
- "It's hard because Y" → solving Y is an idea
- Complaints often contain feature requests

## Raw Ideas
Even half-formed thoughts worth capturing:
- Quick asides
- "Random idea but..."
- Ideas dismissed or tabled

Don't filter - capture everything. A casual mention today might be tomorrow's priority.
"""

ACTION_ITEMS_PROMPT = """
Extract ALL action items, tasks, and next steps from this meeting.

# Action Items

## Assigned Tasks
Tasks with clear ownership:
- [Timestamp] Task: [description]
- Owner: [who is responsible]
- Deadline: [if mentioned]
- Context: [why this task matters]

## Unassigned Tasks
Things that need to happen but no owner yet:
- Task description
- Why it was raised

## Next Steps
General direction/momentum items:
- What happens after this meeting
- Follow-up activities discussed

## Follow-ups
Items needing future attention:
- Questions to research
- People to contact
- Things to verify

Look for phrases like:
- "I'll..." / "You'll..." / "We need to..."
- "Can you..." / "Let's make sure..."
- "Action item:"
- "Next step is..."
- "By [date]..."
"""

FRAMEWORKS_PROMPT = """
Extract all mental models, frameworks, principles, and philosophies from this meeting.

# Frameworks & Philosophies

## Mental Models
Ways of thinking about problems:
- [Timestamp] Framework: [description]
- How it was applied in discussion

## Principles
Guiding rules mentioned:
- "We always..."
- "The rule is..."
- "Our approach is..."

## Philosophies
Team beliefs and working principles:
- Values expressed
- Cultural statements
- How the team thinks about their work

## Ways of Thinking
Interesting perspectives shared:
- Novel approaches to problems
- Reframes of situations
- Strategic lenses applied

Look for:
- Explanatory analogies
- "The way I think about it..."
- "Our philosophy is..."
- Repeated principles/values
- Asides that reveal beliefs
"""

STATUS_UPDATES_PROMPT = """
Extract ALL status updates and state changes from this meeting.

# Status Updates

## Projects Now Live/Complete
Things that shipped or finished:
- [Timestamp] "[Project/Feature] is now live/done"
- What changed
- Impact discussed

## Projects In Progress
Active work updates:
- Current state
- Progress made
- Expected completion

## Projects Blocked/On Hold
Things that are stuck:
- What is blocked
- Why it's blocked
- What would unblock it

## Changes in Priority
Shifts in importance:
- Things moving up
- Things moving down
- Reasons for changes

## Timeline Updates
Schedule changes:
- Delays announced
- Accelerations
- New deadlines set

Look for:
- "X is now..."
- "We shipped..."
- "That's done..."
- "We're waiting on..."
- "The new timeline is..."
"""

BLOCKERS_PROMPT = """
Identify ALL blockers, obstacles, and impediments mentioned in this meeting.

# Blockers & Obstacles

## Technical Blockers
Technical issues preventing progress:
- [Timestamp] Blocker: [description]
- Impact: what can't proceed
- Proposed solution (if discussed)

## Dependencies
Waiting on external factors:
- People to respond
- Decisions from others
- Resources needed

## Resource Constraints
Limitations mentioned:
- Time constraints
- Budget limitations
- Capacity issues

## Knowledge Gaps
Information needed:
- Things we don't know yet
- Research needed
- Expertise required

## Process Blockers
Organizational friction:
- Approval processes
- Coordination challenges
- Communication issues

## Risks Identified
Potential future blockers:
- Concerns raised
- Things that could go wrong
- Uncertainties flagged

Look for:
- "We can't until..."
- "We're blocked on..."
- "The issue is..."
- "We need to figure out..."
- "The risk is..."
"""

# ============================================================================
# Utility Functions
# ============================================================================

def log(message):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {message}", flush=True)


def format_file_size(size_bytes):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def calculate_upload_timeout(file_size_bytes):
    """Calculate appropriate upload timeout based on file size"""
    # Estimate ~1-2 minutes per 100MB, with minimum of 5 minutes
    size_mb = file_size_bytes / (1024 * 1024)
    estimated_timeout = max(300, int(size_mb * 1.5 * 60))  # 1.5 min per 100MB
    return min(estimated_timeout, MAX_UPLOAD_TIMEOUT)


# ============================================================================
# Video Upload with Large File Support
# ============================================================================

# Set by _upload_via_new_sdk so the cleanup block in process_meeting can delete
# the uploaded file through the same client that created it.
_NEW_SDK_CLEANUP = [None]


def _upload_via_new_sdk(video_path):
    """
    Fallback for new-format (non-AIza, e.g. "AQ.") API keys.

    The deprecated google-generativeai file client bootstraps through the
    Discovery API with the key as a ?key= query param, which rejects
    new-format keys (API_KEY_INVALID) even when the key itself is valid.
    The google-genai SDK uploads via header auth, which works. Generation
    calls in the old SDK use gRPC header auth and are unaffected, so we
    hand back a protos.Part file reference the old SDK accepts.
    """
    from google import genai as genai_new

    client = genai_new.Client(api_key=os.environ["GEMINI_API_KEY"])
    upload_start = time.time()
    new_file = client.files.upload(file=str(video_path))
    log(f"  [google-genai] Upload complete in {time.time() - upload_start:.1f}s, name: {new_file.name}")

    poll_interval = PROCESSING_POLL_INTERVAL_START
    total_wait = 0
    while new_file.state.name == "PROCESSING":
        log(f"  [google-genai] Processing... (waited {total_wait}s, checking every {poll_interval}s)")
        time.sleep(poll_interval)
        total_wait += poll_interval
        poll_interval = min(poll_interval * 1.5, PROCESSING_POLL_INTERVAL_MAX)
        new_file = client.files.get(name=new_file.name)

    if new_file.state.name == "FAILED":
        raise Exception(f"Video processing failed: {new_file.state.name}")

    log(f"  [google-genai] Video ready! State: {new_file.state.name}")
    log(f"  Total processing time: {total_wait}s")

    _NEW_SDK_CLEANUP[0] = lambda: client.files.delete(name=new_file.name)
    return genai.protos.Part(
        file_data=genai.protos.FileData(
            file_uri=new_file.uri, mime_type=new_file.mime_type
        )
    )


def upload_video(video_path):
    """
    Upload video to Gemini and wait for processing.

    Supports large files (1-2GB+) with:
    - Progress logging
    - Extended timeouts based on file size
    - Exponential backoff for processing status polling
    """
    log(f"Uploading video: {video_path}")
    file_size = os.path.getsize(video_path)
    log(f"  File size: {format_file_size(file_size)}")

    # Calculate appropriate timeout
    upload_timeout = calculate_upload_timeout(file_size)
    log(f"  Upload timeout: {upload_timeout // 60} minutes")

    # Large file warning
    if file_size > 500 * 1024 * 1024:  # > 500MB
        log("  NOTE: Large file detected. Upload may take several minutes.")
        log("  The google.generativeai SDK handles resumable uploads automatically.")

    upload_start = time.time()

    # Set socket timeout to match calculated upload timeout
    original_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(upload_timeout)
    log(f"  Socket timeout set to {upload_timeout}s for upload")

    try:
        # The SDK handles resumable uploads automatically for large files
        video_file = genai.upload_file(path=str(video_path))
        upload_duration = time.time() - upload_start
        log(f"  Upload complete in {upload_duration:.1f}s, name: {video_file.name}")
    except Exception as e:
        log(f"  Upload failed: {e}")
        if "API_KEY_INVALID" in str(e) or "API key not valid" in str(e):
            log("  New-format API key detected; retrying upload via the google-genai SDK (header auth)")
            return _upload_via_new_sdk(video_path)
        raise
    finally:
        # Restore original socket timeout
        socket.setdefaulttimeout(original_timeout)

    # Wait for processing with exponential backoff
    poll_interval = PROCESSING_POLL_INTERVAL_START
    total_wait = 0

    while video_file.state.name == "PROCESSING":
        log(f"  Processing... (waited {total_wait}s, checking every {poll_interval}s)")
        time.sleep(poll_interval)
        total_wait += poll_interval

        # Exponential backoff up to max interval
        poll_interval = min(poll_interval * 1.5, PROCESSING_POLL_INTERVAL_MAX)

        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise Exception(f"Video processing failed: {video_file.state.name}")

    log(f"  Video ready! State: {video_file.state.name}")
    log(f"  Total processing time: {total_wait}s")
    return video_file


# ============================================================================
# Analysis Functions
# ============================================================================

def analyze_with_prompt(model, video_file, prompt, description, output_dir=None, output_file=None):
    """
    Run analysis with a specific prompt.

    Includes retry logic for robustness and checkpoint saves for long extractions.
    """
    log(f"Analyzing: {description}")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = model.generate_content(
                [video_file, prompt],
                generation_config={"max_output_tokens": MAX_OUTPUT_TOKENS},
                request_options={"timeout": API_CALL_TIMEOUT}
            )
            log(f"  Complete! Response length: {len(response.text)} chars")

            # Checkpoint save if output location provided
            if output_dir and output_file:
                checkpoint_save(output_dir, output_file, response.text, description)

            return response.text

        except Exception as e:
            log(f"  Attempt {attempt}/{MAX_RETRIES} failed: {e}")

            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY_BASE * (2 ** (attempt - 1))
                log(f"  Retrying in {delay}s...")
                time.sleep(delay)
            else:
                log(f"  All retries exhausted for {description}")
                return f"Error generating {description} after {MAX_RETRIES} attempts: {e}"


def checkpoint_save(output_dir, filename, content, description):
    """Save content immediately as a checkpoint"""
    output_path = output_dir / filename

    # Add title header if not already in content
    if not content.strip().startswith("#"):
        title = description.replace("_", " ").title()
        content = f"# {title}\n\n{content}"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    log(f"  Checkpoint saved: {filename}")


def save_output(output_dir, filename, content, title=None):
    """Save content to markdown file"""
    output_path = output_dir / filename

    # Add title header if not already in content
    if title and not content.strip().startswith("#"):
        content = f"# {title}\n\n{content}"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    log(f"Saved: {filename} ({len(content)} chars)")


def get_video_duration(video_path):
    """Return video duration in seconds via ffprobe, or None if unavailable."""
    import subprocess
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error",
             "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1",
             str(video_path)],
            capture_output=True, text=True, timeout=60,
        )
        return float(result.stdout.strip())
    except Exception as e:
        log(f"  Could not probe duration with ffprobe: {e}")
        return None


def maybe_extract_audio(media_path, output_dir):
    """
    For long/large VIDEO inputs, extract the audio stream and return its path so
    the rest of the pipeline processes audio instead of video. Returns the original
    path unchanged for short videos, audio inputs, or if ffmpeg is unavailable.

    Why: see AUDIO_FIRST_* constants. Long videos break the File API 2 GiB cap and
    the windowed transcription. Audio sidesteps both. Stream-copies the existing
    codec (no re-encode, no quality loss, seconds to run).
    """
    import subprocess

    media_path = Path(media_path)
    if media_path.suffix.lower() not in VIDEO_SUFFIXES:
        return media_path  # already audio (or unknown container) - leave it

    size = media_path.stat().st_size
    duration = get_video_duration(media_path) or 0
    if size < AUDIO_FIRST_SIZE_BYTES and duration < AUDIO_FIRST_DURATION_SECONDS:
        return media_path  # short and small enough - keep full multimodal video

    audio_path = Path(output_dir) / (media_path.stem + "_audio.m4a")
    log(f"  Audio-first: video is {format_file_size(size)} / {duration / 60:.0f} min "
        f"(>= threshold). Extracting audio to {audio_path.name} ...")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(media_path),
             "-vn", "-c:a", "copy", "-movflags", "+faststart", str(audio_path)],
            capture_output=True, text=True, timeout=600, check=True,
        )
    except Exception as e:
        # Copy can fail for exotic audio codecs; retry with an AAC re-encode.
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(media_path),
                 "-vn", "-c:a", "aac", "-b:a", "128k", str(audio_path)],
                capture_output=True, text=True, timeout=1200, check=True,
            )
        except Exception as e2:
            log(f"  Audio extraction failed ({e2}); falling back to the video file. "
                f"Note: a video over 2 GiB will be rejected by the File API.")
            return media_path
    log(f"  Audio extracted: {format_file_size(audio_path.stat().st_size)}")
    return audio_path


# Phrases a model returns when a requested transcription window has no content -
# the signature of the long-video duration-misparse failure.
_TRANSCRIPT_REFUSAL_MARKERS = (
    "no video or audio content",
    "no content between",
    "does not contain the requested",
    "bounds of this video",
    "provide a video that contains",
)


def _format_ts(seconds):
    """Seconds -> HH:MM:SS."""
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


def generate_full_transcript(model, video_file, video_path, output_dir,
                             output_file="transcript.md"):
    """
    Produce a COMPLETE verbatim transcript by transcribing the video in
    contiguous time windows and concatenating the segments.

    A single transcription call over a long recording truncates early (e.g.
    stopping ~10 minutes into a 47-minute meeting), so the verbatim record is
    lost even though the model has seen the whole video. Windowing the request
    forces full coverage. Each segment is checkpointed so partial progress
    survives a crash. Falls back to a single pass if duration is unknown.
    """
    duration = get_video_duration(video_path)
    if not duration or duration <= 0:
        log("  Duration unknown - falling back to single-pass transcript")
        return analyze_with_prompt(
            model, video_file, TRANSCRIPT_PROMPT, "transcript",
            output_dir, output_file
        )

    chunk = TRANSCRIPT_CHUNK_MINUTES * 60
    windows = []
    start = 0.0
    while start < duration:
        windows.append((start, min(start + chunk, duration)))
        start += chunk

    log(f"  Transcribing {duration:.0f}s in {len(windows)} window(s) "
        f"of {TRANSCRIPT_CHUNK_MINUTES} min")

    segments = []
    empty_windows = 0
    for i, (w_start, w_end) in enumerate(windows, 1):
        s_ts, e_ts = _format_ts(w_start), _format_ts(w_end)
        prompt = TRANSCRIPT_CHUNK_PROMPT.format(start=s_ts, end=e_ts)
        seg = analyze_with_prompt(
            model, video_file, prompt,
            f"transcript segment {i}/{len(windows)} ({s_ts}-{e_ts})"
        )
        # Coverage check: detect the long-video failure where the model claims a
        # window has no content (it mis-parsed the total duration).
        seg_low = seg.lower()
        if any(m in seg_low for m in _TRANSCRIPT_REFUSAL_MARKERS) or len(seg.strip()) < 80:
            empty_windows += 1
            log(f"  WARNING: window {i}/{len(windows)} ({s_ts}-{e_ts}) returned little/no "
                f"content - the model may have mis-parsed the runtime.")
        segments.append(f"<!-- Segment {i}: {s_ts} - {e_ts} -->\n\n{seg.strip()}")

        # Incremental checkpoint after each window
        partial = "# Meeting Transcript\n\n" + "\n\n".join(segments)
        with open(output_dir / output_file, "w", encoding="utf-8") as f:
            f.write(partial)
        log(f"  Checkpoint saved after segment {i}/{len(windows)}")

    if empty_windows:
        log(f"  COVERAGE WARNING: {empty_windows}/{len(windows)} windows came back empty. "
            f"If this was a long VIDEO, re-run on the extracted audio "
            f"(ffmpeg -i in -vn -c:a copy out.m4a) for a clean transcript.")

    return "# Meeting Transcript\n\n" + "\n\n".join(segments)


# ============================================================================
# Main Processing Pipeline
# ============================================================================

def process_meeting(video_path, output_dir=None):
    """
    Main processing pipeline.

    Args:
        video_path: Path to the video file
        output_dir: Directory to save outputs (defaults to video's directory)
    """
    video_path = Path(video_path).resolve()

    if output_dir is None:
        output_dir = video_path.parent
    else:
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

    log("=" * 60)
    log("Meeting Video Processor - Knowledge Architect")
    log("=" * 60)

    # Verify video exists
    if not video_path.exists():
        log(f"ERROR: Video not found at {video_path}")
        sys.exit(1)

    # Verify API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log("ERROR: GEMINI_API_KEY environment variable not set")
        sys.exit(1)

    genai.configure(api_key=api_key)

    log(f"Video: {video_path.name}")
    log(f"  Size: {format_file_size(video_path.stat().st_size)}")
    log(f"Model: {MODEL_NAME}")
    log(f"Output: {output_dir}")
    log("")

    # Audio-first: for long/large videos, process the audio track instead (avoids
    # the 2 GiB File API cap and the long-video duration-misparse bug). Returns the
    # original path for short videos and audio inputs. All downstream stages and the
    # duration probe operate on this media_path.
    media_path = maybe_extract_audio(video_path, output_dir)

    # Upload the media (audio if extracted, otherwise the original video)
    video_file = upload_video(media_path)

    # Initialize model
    log(f"Initializing model: {MODEL_NAME}")
    model = genai.GenerativeModel(f"models/{MODEL_NAME}")

    # Track what we've processed
    processed = []

    try:
        # Stage 1: Full Transcript
        log("")
        log("=" * 40)
        log("STAGE 1: Full Transcript")
        log("=" * 40)
        # Windowed transcription guarantees full coverage; single-pass
        # transcription truncates long recordings early.
        transcript = generate_full_transcript(
            model, video_file, media_path, output_dir, "transcript.md"
        )
        save_output(output_dir, "transcript.md", transcript)
        processed.append("transcript.md")

        # Stage 2: Meeting Summary
        log("")
        log("=" * 40)
        log("STAGE 2: Meeting Summary")
        log("=" * 40)
        summary = analyze_with_prompt(
            model, video_file, SUMMARY_PROMPT, "meeting summary",
            output_dir, "meeting-summary.md"
        )
        save_output(output_dir, "meeting-summary.md", summary)
        processed.append("meeting-summary.md")

        # Stage 3: Knowledge Extraction
        extractions = [
            ("decisions.md", DECISIONS_PROMPT, "decisions"),
            ("ideas.md", IDEAS_PROMPT, "ideas"),
            ("action-items.md", ACTION_ITEMS_PROMPT, "action items"),
            ("frameworks.md", FRAMEWORKS_PROMPT, "frameworks"),
            ("status-updates.md", STATUS_UPDATES_PROMPT, "status updates"),
            ("blockers.md", BLOCKERS_PROMPT, "blockers"),
        ]

        log("")
        log("=" * 40)
        log("STAGE 3: Knowledge Extraction")
        log("=" * 40)

        for filename, prompt, description in extractions:
            content = analyze_with_prompt(
                model, video_file, prompt, description,
                output_dir, filename
            )
            save_output(output_dir, filename, content)
            processed.append(filename)

    finally:
        # Cleanup - delete uploaded file
        log("")
        log("Cleaning up uploaded video from Gemini...")
        try:
            if _NEW_SDK_CLEANUP[0] is not None:
                _NEW_SDK_CLEANUP[0]()
            else:
                genai.delete_file(video_file.name)
            log("  Uploaded file deleted")
        except Exception as e:
            log(f"  Warning: Could not delete uploaded file: {e}")

    # Summary
    log("")
    log("=" * 60)
    log("PROCESSING COMPLETE")
    log("=" * 60)
    log("")
    log("Generated files:")
    for filename in processed:
        filepath = output_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            log(f"  - {filename} ({size:,} bytes)")

    log("")
    log("Verification checklist:")
    log("  [ ] transcript.md - Full verbatim transcript (not skimmed)")
    log("  [ ] meeting-summary.md - Substantial summary (2+ pages for hour+ meeting)")
    log("  [ ] decisions.md - All explicit AND implicit decisions")
    log("  [ ] ideas.md - All feature ideas, even casual mentions")
    log("  [ ] action-items.md - All tasks and next steps")
    log("  [ ] frameworks.md - Mental models and philosophies")
    log("  [ ] status-updates.md - All project status changes")
    log("  [ ] blockers.md - All identified blockers")

    return processed


def main():
    """Entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Process meeting video with Gemini 3 Pro for comprehensive insight extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Process video, output to same directory
    python process_meeting.py meeting.mp4

    # Process video, output to specific directory
    python process_meeting.py meeting.mp4 ./outputs

    # Process large video (1-2GB)
    python process_meeting.py large_meeting.mp4

Environment:
    GEMINI_API_KEY - Required. Your Gemini API key.

Output Files:
    transcript.md       - Full verbatim transcript with timestamps
    meeting-summary.md  - Comprehensive meeting summary
    decisions.md        - Explicit and implicit decisions
    ideas.md            - Feature ideas and project sparks
    action-items.md     - Tasks and next steps
    frameworks.md       - Mental models and philosophies
    status-updates.md   - Project status changes
    blockers.md         - Blockers and obstacles
"""
    )

    parser.add_argument(
        "video_path",
        help="Path to the meeting video file"
    )
    parser.add_argument(
        "output_dir",
        nargs="?",
        default=None,
        help="Output directory (defaults to video's directory)"
    )

    args = parser.parse_args()

    process_meeting(args.video_path, args.output_dir)


if __name__ == "__main__":
    main()
