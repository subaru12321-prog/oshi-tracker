import json
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


def import_from_json(path):
    """
    docs/data.json のようなJSON({"generated_at": ..., "posts": [...]})を読み込み、
    既存のINSERT OR IGNOREロジックでpostsテーブルに取り込む。

    GitHub Actions側でposts.db(バイナリ)を毎回コミットする代わりに、
    既にコミットされているdocs/data.jsonを前回までの状態として復元するために使う。
    id・fetched_atはDB側で採番・自動設定されるものなので取り込まない。
    ファイルが存在しない場合は何もせず0を返す。

    戻り値: 新規に挿入された行数
    """
    path = Path(path)
    if not path.exists():
        return 0

    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    inserted = 0
    for post in payload.get("posts", []):
        ok = insert_post(
            platform=post.get("platform"),
            source_id=post.get("source_id"),
            author=post.get("author"),
            content=post.get("content"),
            url=post.get("url"),
            image_url=post.get("image_url"),
            published_at=post.get("published_at"),
            member=post.get("member"),
        )
        if ok:
            inserted += 1
    return inserted


def list_posts(platform=None, member=None, limit=200, exclude_platforms=None, ascending=False):
    """投稿を新しい順(既定)で返す。

    exclude_platforms: 除外したいplatform名のリスト。
        スケジュールは未来の日付を持つため、絞り込みなしの一覧に混ぜると
        常に先頭に居座ってしまう。呼び出し側でここに渡して除外する。
    ascending: Trueにすると古い順。スケジュールを「近い予定から」見せる用。
    """
    query = "SELECT * FROM posts"
    conditions = []
    params = []
    if platform:
        conditions.append("platform = ?")
        params.append(platform)
    if member:
        conditions.append("member = ?")
        params.append(member)
    if exclude_platforms:
        placeholders = ", ".join("?" for _ in exclude_platforms)
        conditions.append(f"platform NOT IN ({placeholders})")
        params.extend(exclude_platforms)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += f" ORDER BY published_at {'ASC' if ascending else 'DESC'} LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def list_members():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT member FROM posts WHERE member IS NOT NULL ORDER BY member"
        ).fetchall()
        return [row["member"] for row in rows]
