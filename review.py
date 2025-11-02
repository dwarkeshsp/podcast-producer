import argparse
import json
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for
from main import iterate_on_clip

app = Flask(__name__)
EPISODE_NAME = None


def get_clips_dir():
    """Get the clips directory for the current episode."""
    return Path("episodes") / EPISODE_NAME / "clips"


def load_clip_metadata(hook):
    """Load metadata for a specific clip."""
    metadata_path = get_clips_dir() / f"{hook}_metadata.json"
    with open(metadata_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_clip_metadata(hook, metadata):
    """Save metadata for a specific clip."""
    metadata_path = get_clips_dir() / f"{hook}_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def get_all_clips():
    """Get all clips with their metadata."""
    clips_dir = get_clips_dir()
    clips = []
    
    for metadata_file in sorted(clips_dir.glob("*_metadata.json")):
        hook = metadata_file.stem.replace("_metadata", "")
        metadata = load_clip_metadata(hook)
        
        # Add status if not present
        if "status" not in metadata:
            metadata["status"] = "draft"
            save_clip_metadata(hook, metadata)
        
        # Get video duration
        total_duration = sum(t["duration_ms"] for t in metadata["timestamps"]) / 1000
        
        clips.append({
            "hook": hook,
            "status": metadata["status"],
            "duration": total_duration,
            "num_segments": len(metadata["segment_transcripts"]),
        })
    
    return clips


@app.route("/")
def index():
    """List all clips."""
    clips = get_all_clips()
    draft_clips = [c for c in clips if c["status"] == "draft"]
    approved_clips = [c for c in clips if c["status"] == "approved"]
    
    return render_template(
        "index.html",
        episode_name=EPISODE_NAME,
        draft_clips=draft_clips,
        approved_clips=approved_clips,
    )


@app.route("/clip/<hook>")
def view_clip(hook):
    """View and edit a specific clip."""
    metadata = load_clip_metadata(hook)
    
    # Calculate navigation
    all_clips = get_all_clips()
    current_idx = next((i for i, c in enumerate(all_clips) if c["hook"] == hook), 0)
    prev_hook = all_clips[current_idx - 1]["hook"] if current_idx > 0 else None
    next_hook = all_clips[current_idx + 1]["hook"] if current_idx < len(all_clips) - 1 else None
    
    return render_template(
        "clip.html",
        hook=hook,
        metadata=metadata,
        episode_name=EPISODE_NAME,
        current=current_idx + 1,
        total=len(all_clips),
        prev_hook=prev_hook,
        next_hook=next_hook,
    )


@app.route("/clip/<hook>/save", methods=["POST"])
def save_tweet(hook):
    """Save edited tweet text."""
    metadata = load_clip_metadata(hook)
    metadata["tweet_text"] = request.form["tweet_text"]
    save_clip_metadata(hook, metadata)
    return redirect(url_for("view_clip", hook=hook))


@app.route("/clip/<hook>/iterate", methods=["POST"])
def iterate(hook):
    """Iterate on clip with feedback."""
    feedback = request.form["feedback"]
    iterate_on_clip(EPISODE_NAME, hook, feedback)
    return redirect(url_for("view_clip", hook=hook))


@app.route("/clip/<hook>/approve", methods=["POST"])
def approve(hook):
    """Approve clip for scheduling."""
    metadata = load_clip_metadata(hook)
    metadata["status"] = "approved"
    save_clip_metadata(hook, metadata)
    
    # Navigate to next draft clip
    all_clips = get_all_clips()
    draft_clips = [c for c in all_clips if c["status"] == "draft"]
    
    if draft_clips:
        return redirect(url_for("view_clip", hook=draft_clips[0]["hook"]))
    else:
        return redirect(url_for("index"))


@app.route("/video/<hook>.mp4")
def serve_video(hook):
    """Serve video files."""
    from flask import send_from_directory
    clips_dir = get_clips_dir()
    return send_from_directory(clips_dir, f"{hook}.mp4")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("episode_name", help="Episode name (e.g., 'karpathy')")
    parser.add_argument("--port", type=int, default=5000, help="Port to run on")
    args = parser.parse_args()
    
    global EPISODE_NAME
    EPISODE_NAME = args.episode_name
    
    # Check if episode exists
    clips_dir = get_clips_dir()
    if not clips_dir.exists():
        print(f"Error: {clips_dir} not found. Generate clips first with: python main.py {args.episode_name}")
        return
    
    print(f"\n{'='*60}")
    print(f"Podcast Clip Review - {args.episode_name}")
    print(f"{'='*60}")
    print(f"\nOpen: http://localhost:{args.port}")
    print("Press Ctrl+C to quit\n")
    
    app.run(debug=True, port=args.port)


if __name__ == "__main__":
    main()

