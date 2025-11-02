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

### Start the Web UI

```bash
uv run review.py
```

Opens at `http://localhost:5000` - Everything can be done from the UI!

### From the UI you can:

1. **View all episodes** - See all episodes in `episodes/` directory
2. **Generate clips** - Click "Generate Clips" for any episode with video.mp4
3. **Review clips** - View, edit, and approve clips
4. **Iterate** - Give feedback to regenerate specific clips

### Adding a New Episode

```bash
mkdir -p episodes/karpathy
cp /path/to/video.mp4 episodes/karpathy/video.mp4
```

Then click "Generate Clips" in the UI!

### CLI Usage (Optional)

```bash
# Generate clips via CLI
uv run main.py karpathy

# Iterate on a specific clip
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

