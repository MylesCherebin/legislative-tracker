import whisper
from pathlib import Path

TRANSCRIPT_DIR = Path("transcripts")
TRANSCRIPT_DIR.mkdir(exist_ok=True)

_model = None

def get_model():
    global _model
    if _model is None:
        print("Loading Whisper model (small)...")
        _model = whisper.load_model("small")
    return _model


def transcribe(audio_path, filename_hint, source):
    model = get_model()

    try:
        print(f"Transcribing {audio_path} ...")
        result = model.transcribe(audio_path, fp16=False) 
        text = result["text"].strip()

        safe_name = "".join(c for c in filename_hint if c.isalnum() or c in "-_.")
        out_path = TRANSCRIPT_DIR / f"{source}_{safe_name}.txt"

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)

        return str(out_path)

    except Exception as e:
        print(f"Transcription failed for {audio_path}: {e}")
        return None