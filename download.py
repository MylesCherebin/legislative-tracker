import subprocess
import os
from pathlib import Path

AUDIO_DIR = Path("audio_temp")
AUDIO_DIR.mkdir(exist_ok=True)

def download_audio(video_url, filename_hint, source):
    
    # sanitize filename so it's safe across OSes
    safe_name = "".join(c for c in filename_hint if c.isalnum() or c in "-_.")
    output_template = str(AUDIO_DIR / f"{source}_{safe_name}.%(ext)s")

    cmd = [
        "yt-dlp",
        "-x",                      # extract audio only
        "--audio-format", "mp3",
        "--audio-quality", "5",    
        "-o", output_template,
        video_url
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  
        )
        if result.returncode != 0:
            print(f"yt-dlp failed for {video_url}:\n{result.stderr}")
            return download_audio_fallback(video_url, filename_hint, source)

        
        expected_path = AUDIO_DIR / f"{source}_{safe_name}.mp3"
        if expected_path.exists():
            return str(expected_path)

       
        matches = list(AUDIO_DIR.glob(f"{source}_{safe_name}.*"))
        return str(matches[0]) if matches else None

    except subprocess.TimeoutExpired:
        print(f"Download timed out for {video_url}")
        return None


def download_audio_fallback(video_url, filename_hint, source):
   import requests

    safe_name = "".join(c for c in filename_hint if c.isalnum() or c in "-_.")
    raw_path = AUDIO_DIR / f"{source}_{safe_name}_raw.mp4"
    audio_path = AUDIO_DIR / f"{source}_{safe_name}.mp3"

    try:
        with requests.get(video_url, stream=True, timeout=(15, 120),  # (connect timeout, read timeout) — 120s per chunk
            headers={"User-Agent": "Mozilla/5.0"}) as r:
            r.raise_for_status()
            with open(raw_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        # extract audio with ffmpeg
        subprocess.run(
            ["ffmpeg", "-i", str(raw_path), "-vn", "-acodec", "libmp3lame",
             "-q:a", "5", str(audio_path), "-y"],
            check=True,
            capture_output=True
        )
        return str(audio_path)

    except Exception as e:
        print(f"Fallback download failed for {video_url}: {e}")
        return None
    finally:
        if raw_path.exists():
            raw_path.unlink()  


def cleanup_audio(audio_path):
    try:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
    except Exception as e:
        print(f"Could not delete {audio_path}: {e}")