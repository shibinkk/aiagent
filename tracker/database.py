"""
tracker/database.py
SQLite database layer — stores all job listings and application history.
"""

import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from loguru import logger


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jobs.db"
_db_initialized = False


def init_db():
    """Create tables if they don't exist."""
    global _db_initialized
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            job_hash        TEXT UNIQUE NOT NULL,
            title           TEXT NOT NULL,
            company         TEXT NOT NULL,
            location        TEXT,
            platform        TEXT NOT NULL,
            job_url         TEXT,
            description     TEXT,
            salary          TEXT,
            date_posted     TEXT,
            date_found      TEXT NOT NULL,
            ai_score        REAL DEFAULT 0,
            ai_summary      TEXT,
            cover_letter    TEXT,
            status          TEXT DEFAULT 'found',
            date_applied    TEXT,
            notes           TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_stats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT NOT NULL,
            jobs_found      INTEGER DEFAULT 0,
            jobs_scored     INTEGER DEFAULT 0,
            jobs_applied    INTEGER DEFAULT 0,
            avg_score       REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS approval_queue (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id          INTEGER NOT NULL,
            requested_at    TEXT NOT NULL,
            status          TEXT DEFAULT 'pending',
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        );
    """)

    conn.commit()
    conn.close()
    _db_initialized = True
    logger.info("Database initialised at {}", DB_PATH)


def get_connection() -> sqlite3.Connection:
    global _db_initialized
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _db_initialized:
        init_db()
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def make_hash(title: str, company: str, platform: str) -> str:
    raw = f"{title.lower().strip()}{company.lower().strip()}{platform.lower()}"
    return hashlib.md5(raw.encode()).hexdigest()


def job_exists(job_hash: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM jobs WHERE job_hash = ?", (job_hash,)
    ).fetchone()
    conn.close()
    return row is not None


def insert_job(job: dict) -> int | None:
    """Insert a new job; returns new row id or None if duplicate."""
    job_hash = make_hash(job["title"], job["company"], job["platform"])
    if job_exists(job_hash):
        return None

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO jobs
            (job_hash, title, company, location, platform, job_url,
             description, salary, date_posted, date_found, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        job_hash,
        job.get("title", ""),
        job.get("company", ""),
        job.get("location", ""),
        job.get("platform", ""),
        job.get("job_url", ""),
        job.get("description", ""),
        job.get("salary", ""),
        job.get("date_posted", ""),
        datetime.now().isoformat(timespec="seconds"),
        "found",
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_job_ai(job_id: int, score: float, summary: str, cover_letter: str):
    conn = get_connection()
    conn.execute("""
        UPDATE jobs SET ai_score=?, ai_summary=?, cover_letter=?, status='scored'
        WHERE id=?
    """, (score, summary, cover_letter, job_id))
    conn.commit()
    conn.close()


def update_job_status(job_id: int, status: str):
    conn = get_connection()
    if status == "applied":
        conn.execute(
            "UPDATE jobs SET status=?, date_applied=? WHERE id=?",
            (status, datetime.now().isoformat(timespec="seconds"), job_id),
        )
    else:
        conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
    conn.commit()
    conn.close()


def get_jobs(status: str = None, limit: int = 200) -> list[dict]:
    conn = get_connection()
    if status:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status=? ORDER BY date_found DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY date_found DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pending_approvals() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT j.*, aq.id as queue_id
        FROM approval_queue aq
        JOIN jobs j ON j.id = aq.job_id
        WHERE aq.status = 'pending'
        ORDER BY aq.requested_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_to_approval_queue(job_id: int):
    conn = get_connection()
    conn.execute(
        "INSERT INTO approval_queue (job_id, requested_at) VALUES (?,?)",
        (job_id, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def approve_job(queue_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE approval_queue SET status='approved' WHERE id=?", (queue_id,)
    )
    conn.commit()
    conn.close()


def reject_job(queue_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE approval_queue SET status='rejected' WHERE id=?", (queue_id,)
    )
    conn.commit()
    conn.close()


def get_daily_stats() -> dict:
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT * FROM daily_stats WHERE date=?", (today,)
    ).fetchone()
    if not row:
        conn.execute(
            "INSERT INTO daily_stats (date) VALUES (?)", (today,)
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM daily_stats WHERE date=?", (today,)
        ).fetchone()
    conn.close()
    return dict(row)


def increment_stat(field: str, amount: int = 1):
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        f"UPDATE daily_stats SET {field} = {field} + ? WHERE date=?",
        (amount, today),
    )
    conn.commit()
    conn.close()


def get_stats_summary() -> dict:
    """Returns overall stats for the dashboard."""
    conn = get_connection()
    stats = {}
    for status in ("found", "scored", "applied", "interview", "rejected", "pending_approval"):
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM jobs WHERE status=?", (status,)
        ).fetchone()
        stats[status] = row["cnt"] if row else 0

    # Include queue pending count
    try:
        q_row = conn.execute("SELECT COUNT(*) as cnt FROM approval_queue WHERE status='pending'").fetchone()
        stats["pending_approval"] = max(stats.get("pending_approval", 0), (q_row["cnt"] if q_row else 0))
    except Exception:
        pass

    # Weekly trend
    rows = conn.execute("""
        SELECT date, jobs_applied FROM daily_stats
        ORDER BY date DESC LIMIT 14
    """).fetchall()
    stats["weekly_trend"] = [dict(r) for r in rows]
    conn.close()
    return stats
