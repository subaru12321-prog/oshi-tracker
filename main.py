"""
全プラットフォームの収集を1回実行し、新しい投稿だけをDBに保存する。

定期実行はこのスクリプトをWindowsのタスクスケジューラに登録して行う想定。
"""
import config
import db
from collectors import instagram, showroom, tiktok, x_twitter

# platform名 -> (メンバーのaccountブロックの中でidentifierを取り出すキー, collect関数)
PLATFORM_SPEC = {
    "showroom": ("room_url_key", showroom.collect),
    "instagram": ("username", instagram.collect),
    "x": ("username", x_twitter.collect),
    "tiktok": ("username", tiktok.collect),
}


def build_platform_maps(members):
    """platform -> {identifier: member_name} を組み立てる。"""
    maps = {platform: {} for platform in PLATFORM_SPEC}
    for m in members:
        name = m.get("name")
        for platform, (id_key, _fn) in PLATFORM_SPEC.items():
            account = m.get(platform)
            if not account:
                continue
            identifier = account.get(id_key)
            if identifier:
                maps[platform][identifier] = name
    return maps


def run_once():
    db.init_db()
    cfg = config.load_config()
    members = cfg.get("members", [])
    platform_maps = build_platform_maps(members)

    total_new = 0
    for platform, (_id_key, collect_fn) in PLATFORM_SPEC.items():
        identifiers = list(platform_maps[platform].keys())
        if not identifiers:
            continue
        try:
            posts = collect_fn(identifiers)
        except Exception as e:
            print(f"[{platform}] 収集全体でエラー: {e}")
            continue

        new_count = 0
        for post in posts:
            identifier = post.pop("identifier", None)
            post["member"] = platform_maps[platform].get(identifier)
            if db.insert_post(**post):
                new_count += 1
        total_new += new_count
        print(f"[{platform}] 取得 {len(posts)} 件 / 新規 {new_count} 件")

    print(f"合計 新規 {total_new} 件")


if __name__ == "__main__":
    run_once()
