import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "posts.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    source_id TEXT NOT NULL,
    member TEXT,
    author TEXT,
    content TEXT,
    url TEXT,
    image_url TEXT,
    published_at TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(platform, source_id)
);
CREATE INDEX IF NOT EXISTS idx_posts_published_at ON posts(published_at DESC);
"""


def _migrate(conn):
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(posts)")}
    if "member" not in cols:
        conn.execute("ALTER TABLE posts ADD COLUMN member TEXT")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)


def insert_post(platform, source_id, author, content, url, image_url, published_at, member=None):
    """Returns True if a new row was inserted, False if it already existed."""
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO posts
                (platform, source_id, member, author, content, url, image_url, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (platform, source_id, member, author, content, url, image_url, published_at),
        )
        return cur.rowcount > 0


def list_posts(platform=None, member=None, limit=200):
    query = "SELECT * FROM posts"
    conditions = []
    params = []
    if platform:
        conditions.append("platform = ?")
        params.append(platform)
    if member:
        conditions.append("member = ?")
        params.append(member)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY published_at DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def list_members():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT member FROM posts WHERE member IS NOT NULL ORDER BY member"
        ).fetchall()
        return [row["member"] for row in rows]
