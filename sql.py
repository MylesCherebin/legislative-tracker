import sqlite3
from datetime import datetime, timezone

MAX_RETRIES = 3

def init_db(db_path="videos.db"):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            video_id TEXT,
            download_url TEXT,
            captions_url TEXT,
            captioned_flag INTEGER DEFAULT 0,
            title TEXT,
            source TEXT,
            discovered_at TEXT,
            transcribed_at TEXT,
            transcript_path TEXT,
            transcript_source TEXT,
            status TEXT DEFAULT 'pending',
            retry_count INTEGER DEFAULT 0,
            last_error TEXT,
            last_attempted_at TEXT
        )
    """)
    con.commit()
    return con


def add_video(con, url, title, source, video_id=None, captioned_flag=False,
               download_url=None, captions_url=None):
    """Returns True if new, False if already seen."""
    try:
        con.execute(
            """INSERT INTO videos
               (url, video_id, captioned_flag, download_url, captions_url,
                title, source, discovered_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (url, video_id, int(captioned_flag), download_url, captions_url,
             title, source, datetime.now(timezone.utc).isoformat())
        )
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_pending(con):
    """
    Returns videos that still need processing:
      - never attempted (pending)
      - stuck mid-run from a crashed previous run (processing)
      - errored but still under the retry cap
    """
    return con.execute(
        """SELECT * FROM videos
           WHERE status = 'pending'
              OR status = 'processing'
              OR (status = 'error' AND retry_count < ?)
           ORDER BY retry_count ASC, discovered_at ASC""",
        (MAX_RETRIES,)
    ).fetchall()


def mark_processing(con, url):
    """Call this right before starting work on a video, so crashes are recoverable."""
    con.execute(
        "UPDATE videos SET status='processing', last_attempted_at=? WHERE url=?",
        (datetime.now(timezone.utc).isoformat(), url)
    )
    con.commit()


def mark_done(con, url, transcript_path, transcript_source):
    con.execute(
        """UPDATE videos
           SET status='done', transcribed_at=?, transcript_path=?, transcript_source=?
           WHERE url=?""",
        (datetime.now(timezone.utc).isoformat(), transcript_path, transcript_source, url)
    )
    con.commit()


def mark_error(con, url, error_message=""):
    con.execute(
        """UPDATE videos
           SET status='error',
               retry_count = retry_count + 1,
               last_error = ?,
               last_attempted_at = ?
           WHERE url=?""",
        (str(error_message)[:1000], datetime.now(timezone.utc).isoformat(), url)  # cap length
    )
    con.commit()


def get_permanently_failed(con):
    """Videos that exhausted their retries — surface these for a human to check."""
    return con.execute(
        "SELECT * FROM videos WHERE status = 'error' AND retry_count >= ?",
        (MAX_RETRIES,)
    ).fetchall()