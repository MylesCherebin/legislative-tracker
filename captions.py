import requests
import re

def fetch_vtt_captions(captions_url):
    try:
        response = requests.get(captions_url, timeout=15)
        response.raise_for_status()
        vtt_text = response.text

        if "WEBVTT" not in vtt_text[:20]:
            return None  # not actually a VTT file

        lines = vtt_text.splitlines()
        text_lines = []
        for line in lines:
            line = line.strip()
            if (not line
                or line == "WEBVTT"
                or "-->" in line
                or line.isdigit()):
                continue
            clean = re.sub(r"<[^>]+>", "", line)
            text_lines.append(clean)

        text = " ".join(text_lines).strip()
        return text if text else None

    except Exception as e:
        print(f"Could not fetch captions from {captions_url}: {e}")
        return None