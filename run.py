from sql import init_db, get_pending, mark_error, mark_processing, mark_done, get_permanently_failed
from crawlers import (crawl_house, crawl_senate, get_senate_user_id, 
get_senate_captions_url, get_senate_video_url)
from download import download_audio, cleanup_audio
from transcribe import transcribe
from captions import fetch_vtt_captions

def process_house_video(con, video):
    url = video["url"]
    title = video["title"]
    start = title.index("-") + 1
    if int(title[start:start+2]) < 6:
        return False

    mark_processing(con, video["url"])
    source = video["source"]
    download_url = video["download_url"] 
    audio_path = download_audio(download_url, title, source)
    if not audio_path:
        mark_error(con, url)
        return False

    transcript_path = transcribe(audio_path, title, source)
    cleanup_audio(audio_path)

    if transcript_path:
        mark_done(con, url, transcript_path, "whisper")
        return True
    else:
        mark_error(con, url)
        return False

def process_senate_video(con, video):
    url = video["url"]
    title = video["title"]
    source = video["source"]
    video_id = video["video_id"]
    user_id = get_senate_user_id()

    transcript_text = None
    transcript_source = None
    mark_processing(con, video["url"])
    # try captions first 
    if video["captioned_flag"]:
        captions_url = get_senate_captions_url(video_id, user_id) 
        if captions_url:
            transcript_text = fetch_vtt_captions(captions_url)
            if transcript_text:
                transcript_source = "captions"

    if transcript_text:
        return save_transcript_text(con, url, title, source, transcript_text, transcript_source)

    # fall back to downloading the mp4 + whisper
    mp4_url = get_senate_video_url(video_id, user_id)  
    if not mp4_url:
        mark_error(con, url)
        return False

    audio_path = download_audio(mp4_url, title, source)
    if not audio_path:
        mark_error(con, url)
        return False

    transcript_path = transcribe(audio_path, title, source)
    cleanup_audio(audio_path)

    if transcript_path:
        mark_done(con, url, transcript_path, "whisper")
        return True
    else:
        mark_error(con, url)
        return False

def save_transcript_text(con, url, title, source, text, transcript_source):
    safe_name = "".join(c for c in title if c.isalnum() or c in "-_.")
    transcript_path = f"transcripts/{source}_{safe_name}.txt"

    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(text)

    mark_done(con, url, transcript_path, transcript_source)
    return True

def main():
    con = init_db()

    # get new videos add to db
    new_house = crawl_house(con)
    if new_house  != []:
        print("Found new House videos")
    new_senate = crawl_senate(con)
    if new_senate !=  []:
        print("Found new Senate videos")

    #process pending videos
    pending = get_pending(con)
    
    for video in pending:
        title = video["title"]
        source = video["source"]
        retries = video["retry_count"]
        label = f"retry {retries}" if retries > 0 else "first attempt"
        print(f"\n--- Processing: {title} ({source}, {label}) ---")

        try:
            if source == "senate":
                process_senate_video(con, video)
            else:
                # only process videos from june
                start = title.index("-") + 1
                if int(title[start:start+2]) == 6:
                    process_house_video(con, video)
        except Exception as e:
            print(f"Unexpected error processing {title}: {e}")
            mark_error(con, video["url"])
    
    failed = get_permanently_failed(con)
    if failed:
        print(f"\n{len(failed)} video(s) permanently failed after max retries:")
        for f in failed:
            print(f"  - {f['title']}: {f['last_error']}")

    con.close()
    print("Done processing videos")
if __name__ == "__main__":
    main()