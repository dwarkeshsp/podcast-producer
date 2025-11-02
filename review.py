import argparse
import json
import subprocess
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash
from main import iterate_on_clip

app = Flask(__name__)
app.secret_key = "podcast-producer-secret-key"  # For flash messages


def get_all_episodes():
    """Get all episodes from the episodes directory."""
    episodes_dir = Path("episodes")
    if not episodes_dir.exists():
        episodes_dir.mkdir(exist_ok=True)
        return []
    
    episodes = []
    for episode_dir in sorted(episodes_dir.iterdir()):
        if episode_dir.is_dir() and not episode_dir.name.startswith('.'):
            video_path = episode_dir / "video.mp4"
            clips_dir = episode_dir / "clips"
            transcript_path = episode_dir / "transcript.json"
            
            # Check status
            has_video = video_path.exists()
            has_transcript = transcript_path.exists()
            has_clips = clips_dir.exists() and any(clips_dir.glob("*.mp4"))
            
            clip_count = 0
            draft_count = 0
            approved_count = 0
            
            if has_clips:
                for metadata_file in clips_dir.glob("*_metadata.json"):
                    clip_count += 1
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        status = metadata.get('status', 'draft')
                        if status == 'draft':
                            draft_count += 1
                        elif status == 'approved':
                            approved_count += 1
            
            episodes.append({
                'name': episode_dir.name,
                'has_video': has_video,
                'has_transcript': has_transcript,
                'has_clips': has_clips,
                'clip_count': clip_count,
                'draft_count': draft_count,
                'approved_count': approved_count,
            })
    
    return episodes


def get_clips_dir(episode_name):
    """Get the clips directory for a specific episode."""
    return Path("episodes") / episode_name / "clips"


def load_clip_metadata(episode_name, hook):
    """Load metadata for a specific clip."""
    metadata_path = get_clips_dir(episode_name) / f"{hook}_metadata.json"
    with open(metadata_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_clip_metadata(episode_name, hook, metadata):
    """Save metadata for a specific clip."""
    metadata_path = get_clips_dir(episode_name) / f"{hook}_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def get_all_clips(episode_name):
    """Get all clips with their metadata."""
    clips_dir = get_clips_dir(episode_name)
    clips = []
    
    for metadata_file in sorted(clips_dir.glob("*_metadata.json")):
        hook = metadata_file.stem.replace("_metadata", "")
        metadata = load_clip_metadata(episode_name, hook)
        
        # Add status if not present
        if "status" not in metadata:
            metadata["status"] = "draft"
            save_clip_metadata(episode_name, hook, metadata)
        
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
def home():
    """Home page showing all episodes."""
    episodes = get_all_episodes()
    return render_template("home.html", episodes=episodes)


@app.route("/episode/<episode_name>/clips")
def episode_clips(episode_name):
    """List all clips for an episode."""
    clips = get_all_clips(episode_name)
    draft_clips = [c for c in clips if c["status"] == "draft"]
    approved_clips = [c for c in clips if c["status"] == "approved"]
    
    return render_template(
        "clips.html",
        episode_name=episode_name,
        draft_clips=draft_clips,
        approved_clips=approved_clips,
    )


@app.route("/episode/<episode_name>/clip/<hook>")
def view_clip(episode_name, hook):
    """View and edit a specific clip."""
    metadata = load_clip_metadata(episode_name, hook)
    
    # Calculate navigation
    all_clips = get_all_clips(episode_name)
    current_idx = next((i for i, c in enumerate(all_clips) if c["hook"] == hook), 0)
    prev_hook = all_clips[current_idx - 1]["hook"] if current_idx > 0 else None
    next_hook = all_clips[current_idx + 1]["hook"] if current_idx < len(all_clips) - 1 else None
    
    return render_template(
        "clip.html",
        hook=hook,
        metadata=metadata,
        episode_name=episode_name,
        current=current_idx + 1,
        total=len(all_clips),
        prev_hook=prev_hook,
        next_hook=next_hook,
    )


@app.route("/episode/<episode_name>/clip/<hook>/save", methods=["POST"])
def save_tweet(episode_name, hook):
    """Save edited tweet text."""
    metadata = load_clip_metadata(episode_name, hook)
    metadata["tweet_text"] = request.form["tweet_text"]
    save_clip_metadata(episode_name, hook, metadata)
    return redirect(url_for("view_clip", episode_name=episode_name, hook=hook))


@app.route("/episode/<episode_name>/clip/<hook>/iterate", methods=["POST"])
def iterate(episode_name, hook):
    """Iterate on clip with feedback."""
    feedback = request.form["feedback"]
    iterate_on_clip(episode_name, hook, feedback)
    return redirect(url_for("view_clip", episode_name=episode_name, hook=hook))


@app.route("/episode/<episode_name>/clip/<hook>/approve", methods=["POST"])
def approve(episode_name, hook):
    """Approve clip for scheduling."""
    metadata = load_clip_metadata(episode_name, hook)
    metadata["status"] = "approved"
    save_clip_metadata(episode_name, hook, metadata)
    
    # Navigate to next draft clip
    all_clips = get_all_clips(episode_name)
    draft_clips = [c for c in all_clips if c["status"] == "draft"]
    
    if draft_clips:
        return redirect(url_for("view_clip", episode_name=episode_name, hook=draft_clips[0]["hook"]))
    else:
        return redirect(url_for("episode_clips", episode_name=episode_name))


@app.route("/episode/<episode_name>/video/<hook>.mp4")
def serve_video(episode_name, hook):
    """Serve video files."""
    from flask import send_from_directory
    clips_dir = get_clips_dir(episode_name)
    return send_from_directory(clips_dir, f"{hook}.mp4")


@app.route("/episode/<episode_name>/generate", methods=["POST"])
def generate_clips(episode_name):
    """Generate clips for an episode."""
    episode_dir = Path("episodes") / episode_name
    video_path = episode_dir / "video.mp4"
    
    if not video_path.exists():
        flash(f"Error: video.mp4 not found in episodes/{episode_name}/", "error")
        return redirect(url_for("home"))
    
    try:
        # Run main.py to generate clips
        result = subprocess.run(
            ["uv", "run", "main.py", episode_name],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        if result.returncode == 0:
            flash(f"Successfully generated clips for {episode_name}!", "success")
        else:
            flash(f"Error generating clips: {result.stderr}", "error")
    except subprocess.TimeoutExpired:
        flash("Clip generation timed out (30 minutes)", "error")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    
    return redirect(url_for("episode_clips", episode_name=episode_name))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000, help="Port to run on")
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print("Podcast Clip Producer")
    print(f"{'='*60}")
    print(f"\nOpen: http://localhost:{args.port}")
    print("Press Ctrl+C to quit\n")
    
    app.run(debug=True, port=args.port)


if __name__ == "__main__":
    main()

