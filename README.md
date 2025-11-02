# Podcast Clip Producer

Automatically generate and review Twitter clips from podcast episodes.

## Setup

```bash
# Install dependencies
uv sync

# Set environment variables
export ASSEMBLYAI_API_KEY="your_key"
export ANTHROPIC_API_KEY="your_key"
```

## Usage

### 1. Generate Clips

```bash
# Add your video to episodes/{name}/video.mp4
mkdir -p episodes/karpathy
cp /path/to/video.mp4 episodes/karpathy/video.mp4

# Generate clips
uv run main.py karpathy
```

This will:
- Transcribe the video (or load existing transcript)
- Generate 8 clip suggestions with Claude
- Render clips as square videos with tweet text

### 2. Review Clips

```bash
uv run review.py karpathy
```

Opens a web interface at `http://localhost:5000` where you can:
- View all draft and approved clips
- Watch clips alongside tweet text
- Edit tweet text directly
- Give feedback to regenerate clips
- Approve clips for scheduling

### 3. Iterate on a Clip (CLI)

```bash
uv run main.py karpathy --iterate hook_name --feedback "Remove middle segment"
```

## Directory Structure

```
episodes/
  karpathy/
    video.mp4              # Source video
    transcript.json        # Auto-generated transcript
    clips/
      rl_terrible.mp4
      rl_terrible_tweet.txt
      rl_terrible_metadata.json
      ...
```

## Review UI Features

- **Edit Tweet Text**: Update tweet text directly in textarea
- **Give Feedback**: High-level feedback to regenerate clip
- **Approve**: Mark clip for scheduling (Phase 2)
- **Keyboard Shortcuts**:
  - `←` / `→` : Previous/Next clip
  - `Space` : Play/Pause video

## Metadata Format

```json
{
  "hook": "rl_terrible",
  "status": "draft",
  "tweet_text": "...",
  "segment_transcripts": ["...", "..."],
  "timestamps": [...]
}
```

**Status values:**
- `draft` - Needs review
- `approved` - Ready for scheduling (Phase 2)

