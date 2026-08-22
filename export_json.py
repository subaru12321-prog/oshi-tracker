"""
posts.db の内容を docs/data.json に書き出す。
GitHub Pages (docs/) が静的サイトとしてこのJSONを読み込んで表示する。
"""
import datetime
import json
from pathlib import Path

import db

OUT_PATH = Path(__file__).parent / "docs" / "data.json"
MAX_POSTS = 500


def export():
    db.init_db()
    posts = db.list_posts(limit=MAX_POSTS)
    payload = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "posts": posts,
    }
    OUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"{len(posts)} 件を {OUT_PATH} に出力しました")


if __name__ == "__main__":
    export()
