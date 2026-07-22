---
name: meeting-processor
description: Process meeting videos, audio, and images using Gemini 3 Pro models to exhaustively extract insights including transcripts, decisions, action items, ideas, frameworks, status updates, and blockers. Supports large video files (1-2GB+). Use when processing meeting recordings or any media files requiring comprehensive knowledge extraction. Acts as a "knowledge architect" that mines every valuable insight.
---

# Meeting Processor Skill

You are the **knowledge architect** for meeting processing. Your role is to exhaustively mine meeting recordings and meeting artifacts like video, audio and images for every valuable insight, idea, philosophy, decision, and status update.

## Core Principle

**Missing content is unacceptable.**

Meetings are the primary sync mechanism between reality and documented state. Every piece of valuable information must be captured.

## Requirements

### Model Requirement
**MUST use a current Gemini 3.x Pro multimodal model** for all video, audio and image processing. These models have the multimodal capabilities required for meeting analysis. The script's `MODEL_NAME` is set to `gemini-3.1-pro-preview`.

> **Note (2026-06):** Google retired `gemini-3-pro-preview` — `generateContent` returns `404 "no longer available"` even though it still appears in `list_models()`. If the configured model 404s, validate a replacement with a trivial `generate_content("OK")` call and update `MODEL_NAME` in `scripts/process_meeting.py`. Known-good Pro-tier models as of this writing: `gemini-3.1-pro-preview`, `gemini-pro-latest`, `gemini-2.5-pro`.

> **Note (2026-07): new-format API keys.** Google now issues non-`AIzaSy` keys (e.g. prefix `AQ.`). These pass a trivial `generate_content("OK")` check but the deprecated `google-generativeai` SDK's **file upload** fails with `API_KEY_INVALID` — its file client bootstraps through the Discovery API with the key as a `?key=` query param, which rejects new-format keys. The script auto-falls back to the `google-genai` SDK (header auth) for upload/poll/delete and hands generation a `protos.Part` file reference, so both key formats work. Requires `pip install google-genai` for the fallback path. Do not diagnose `API_KEY_INVALID` on upload as a bad key without first checking the key format.

### Environment Setup
```bash
export GEMINI_API_KEY=your_api_key_here
```

### Python Dependencies
```bash
pip install google-generativeai
```

## Processing Workflow

### Step 1: Verify Setup
1. Confirm `GEMINI_API_KEY` environment variable is set
2. Verify video file exists and is accessible
3. Check file size for large file handling needs

### Step 2: Run the Processor
```bash
# Basic usage - outputs to same directory as video
python /Users/rohitkelapure/.claude/skills/meeting-processor/scripts/process_meeting.py <video_path>

# With custom output directory
python /Users/rohitkelapure/.claude/skills/meeting-processor/scripts/process_meeting.py <video_path> <output_dir>
```

### Step 3: Verify Outputs
Check all 8 output files are generated with appropriate depth:
- `transcript.md` - Full verbatim transcript
- `meeting-summary.md` - Comprehensive summary (2-4 pages for hour+ meeting)
- `decisions.md` - Explicit AND implicit decisions
- `ideas.md` - All ideas, even casual mentions
- `action-items.md` - Tasks and next steps
- `frameworks.md` - Mental models and philosophies
- `status-updates.md` - Project state changes
- `blockers.md` - Obstacles and risks

## Long Recordings: Audio-First (IMPORTANT)

Long **videos** fail two ways, and the processor now handles both automatically:

1. **The Gemini File API hard-rejects any file over 2 GiB** (`MediaUploadSizeError: Media larger than 2147483648`).
2. **On long videos the windowed transcription mis-parses the runtime** (observed: a 1:09:16 recording read as 9:16). The model then blanks whole windows ("there is no content between 00:30:00 and 00:40:00"), repeats earlier passages under wrong timestamps, and scrambles speaker labels.

**The fix the script applies:** for a video input at or above ~50 minutes or ~1.8 GiB, it extracts the audio stream (`ffmpeg -i in -vn -c:a copy out_audio.m4a`, a fast stream-copy, no quality loss) into the output directory and processes the **audio** instead. Audio is tiny (~48 MB/hour), uploads in seconds, stays under the cap, and yields correct per-window timestamps. Short videos keep full multimodal processing. The only trade-off is that on-screen slide visuals are not seen; spoken content and insights are intact.

**If you must run it manually** on a long video, extract the audio first yourself and pass the `.m4a`:
```bash
ffmpeg -i meeting.mp4 -vn -c:a copy meeting_audio.m4a
python process_meeting.py meeting_audio.m4a ./outputs
```

**Always verify coverage** before trusting the transcript: confirm the closing timestamp is near the full runtime. The script now logs a `COVERAGE WARNING` if any window returns empty; if you see it on a video run, re-run on the extracted audio.

## Large File Handling (1-2GB+)

The processor is designed to handle large video files:

### Upload Phase
- **Resumable uploads**: The Google SDK handles this automatically for files >100MB
- **Extended timeouts**: Upload timeout scales with file size (~1.5 min per 100MB)
- **Progress logging**: Status updates during upload

### Processing Phase
- **Extended API timeout**: 20 minutes per extraction stage
- **Exponential backoff**: Polling starts at 30s, increases to max 120s
- **Checkpoint saves**: Each output saved immediately after generation
- **Retry logic**: Up to 3 retries per extraction with exponential delay

### Expected Timing for Large Files
| File Size | Upload Time | Processing Time | Total |
|-----------|-------------|-----------------|-------|
| 500MB | 5-10 min | 30-60 min | ~1 hour |
| 1GB | 10-20 min | 45-90 min | ~1.5 hours |
| 2GB | 20-30 min | 60-120 min | ~2.5 hours |

## Extraction Categories

### 1. Transcript
Complete verbatim record with:
- Timestamps every 30-60 seconds
- Speaker identification
- Verbal fillers preserved
- Non-verbal cues: `[laughs]`, `[pause]`, `[crosstalk]`

### 2. Meeting Summary
Comprehensive overview including:
- Participants and context
- Key discussion points
- Critical insights
- Open questions

### 3. Decisions
- **Explicit**: Clearly stated decisions
- **Implicit**: Decisions made by NOT deciding
- **Deferred**: Items pushed to later
- **Rationale**: Reasoning captured

### 4. Ideas
- **Feature ideas**: Enhancements to existing projects
- **Project sparks**: New tool/project concepts
- **Embedded ideas**: Ideas hidden in problem discussions
- **Raw ideas**: Half-formed thoughts worth capturing

### 5. Action Items
- **Assigned tasks**: With owner and deadline
- **Unassigned tasks**: Needing ownership
- **Next steps**: Direction items
- **Follow-ups**: Future attention needed

### 6. Frameworks
- **Mental models**: Ways of thinking
- **Principles**: Guiding rules
- **Philosophies**: Team beliefs
- **Perspectives**: Novel approaches

### 7. Status Updates
- **Live/Complete**: Shipped items
- **In Progress**: Current work
- **Blocked/On Hold**: Stuck items
- **Priority changes**: Shifts in importance
- **Timeline updates**: Schedule changes

### 8. Blockers
- **Technical**: Code/infrastructure issues
- **Dependencies**: External factors
- **Resources**: Constraints
- **Knowledge gaps**: Information needed
- **Process**: Organizational friction
- **Risks**: Potential future blockers

## Hunting for Implicit Content

Always look for hidden insights:

| Surface Pattern | Hidden Content |
|-----------------|----------------|
| "The issue is we don't have X" | X is an idea |
| "It's hard because Y" | Solving Y is an idea |
| "We always say..." | Philosophy |
| "Let's not wait for..." | Decision (implicit) |
| Complaints | Feature requests |
| Problems discussed | Opportunities |

## Acceptance Criteria

Before marking processing complete, verify:

- [ ] Read entire transcript (no skimming)
- [ ] All explicit decisions captured
- [ ] All implicit decisions captured
- [ ] All feature ideas extracted (even casual mentions)
- [ ] All frameworks/philosophies captured
- [ ] All status changes reflected
- [ ] State sync complete

### Red Flags (Incomplete Processing)
- Meeting summary shorter than 1 page for hour+ meeting
- Only 1-2 ideas extracted from brainstorming discussion
- No status changes identified in status-heavy meeting
- Missing implicit content

## Reference Documentation

- **Prompts**: See `references/extraction-prompts.md` for all specialized prompts
- **Output Formats**: See `references/output-formats.md` for file specifications

## Troubleshooting

### API Key Issues
```bash
# Verify API key is set
echo $GEMINI_API_KEY

# If not set, export it
export GEMINI_API_KEY=your_key_here
```

### Upload Failures
- Check network connectivity
- For files over 2 GiB or videos over ~50 min, the script auto-extracts audio (see "Long Recordings: Audio-First"). If it still fails, extract audio manually and pass the `.m4a`. Do not split the video; the windowed transcription does not need it and splitting fragments cross-meeting context.
- The SDK automatically handles resumable uploads

### Processing Timeouts
- Extended timeouts are built in (20 min per stage)
- For extremely long videos (3+ hours), processing may take longer
- Checkpoint saves ensure partial progress is preserved

### Incomplete Outputs
- Check the console logs for error messages
- Retry logic handles transient failures
- If an extraction fails after 3 retries, error message is saved to output file
