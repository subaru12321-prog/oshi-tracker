"""
全プラットフォームの収集を1回実行し、新しい投稿だけをDBに保存する。

定期実行はこのスクリプトをWindowsのタスクスケジューラに登録して行う想定。
"""
from pathlib import Path

import config
import db
import member_match

DOCS_DATA_JSON_PATH = Path(__file__).parent / "docs" / "data.json"

# platform名 -> メンバーのaccountブロックの中でidentifierを取り出すキー
# 収集関数はここでは import せず、_load_collect_fn() で使う直前に遅延importする。
# (TikTokApi/playwrightのようなローカル専用のオプション依存パッケージが
#  未インストールでも、他のプラットフォームの収集まで巻き込んで落ちないようにするため)
PLATFORM_ID_KEYS = {
    "showroom": "room_url_key",
    "instagram": "username",
    "tiktok": "username",
}


def _load_collect_fn(platform):
    """platform名からcollect関数を遅延importして返す。"""
    if platform == "showroom":
        from collectors import showroom
        return showroom.collect
    if platform == "instagram":
        from collectors import instagram
        return instagram.collect
    if platform == "tiktok":
        from collectors import tiktok
        return tiktok.collect
    raise ValueError(f"未知のplatform: {platform}")


# メンバー個人のアカウントに紐づかない、グループ全体の情報源。
# source名 -> config.yaml の sources: 以下でcollect()に渡す引数を入れるキー
GROUP_SOURCE_ARG_KEYS = {
    "official_site": "sections",
    "youtube": "channel_ids",
}


def _load_group_collect_fn(source):
    """グループ全体の情報源のcollect関数を遅延importして返す。"""
    if source == "official_site":
        from collectors import official_site
        return official_site.collect
    if source == "youtube":
        from collectors import youtube
        return youtube.collect
    raise ValueError(f"未知のsource: {source}")


def build_platform_maps(members):
    """platform -> {identifier: member_name} を組み立てる。"""
    maps = {platform: {} for platform in PLATFORM_ID_KEYS}
    for m in members:
        name = m.get("name")
        for platform, id_key in PLATFORM_ID_KEYS.items():
            account = m.get(platform)
            if not account:
                continue
            identifier = account.get(id_key)
            if identifier:
                maps[platform][identifier] = name
    return maps


def collect_group_sources(cfg, member_names):
    """グループ全体の情報源(公式サイト・YouTube)を収集してDBに保存する。

    これらは「アカウント = メンバー」が確定しないため、本文(ニュースや動画の
    タイトル)にメンバー名が含まれていればそれを紐付ける。含まれていなければ
    グループ全体の話題として member は None のままにする。
    """
    sources = cfg.get("sources") or {}
    total_new = 0

    for source, arg_key in GROUP_SOURCE_ARG_KEYS.items():
        args = (sources.get(source) or {}).get(arg_key) or []
        if not args:
            continue
        try:
            collect_fn = _load_group_collect_fn(source)
            posts = collect_fn(args)
        except Exception as e:
            print(f"[{source}] 収集全体でエラー: {e}")
            continue

        new_count = 0
        for post in posts:
            post.pop("identifier", None)
            post["member"] = member_match.find_member(post.get("content"), member_names)
            if db.insert_post(**post):
                new_count += 1
        total_new += new_count
        print(f"[{source}] 取得 {len(posts)} 件 / 新規 {new_count} 件")

    return total_new


def run_once():
    db.init_db()
    restored = db.import_from_json(DOCS_DATA_JSON_PATH)
    print(f"docs/data.json から {restored} 件を復元しました")

    cfg = config.load_config()
    members = cfg.get("members", [])
    member_names = [m["name"] for m in members if m.get("name")]
    platform_maps = build_platform_maps(members)

    total_new = 0
    for platform in PLATFORM_ID_KEYS:
        identifiers = list(platform_maps[platform].keys())
        if not identifiers:
            continue
        try:
            collect_fn = _load_collect_fn(platform)
        except ImportError:
            # TikTokのようにローカル専用のオプション依存を使うものは、
            # クラウドでは未インストールなのが正常。エラー扱いにしない。
            print(f"[{platform}] 依存パッケージが未インストールのためスキップします")
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

    total_new += collect_group_sources(cfg, member_names)

    print(f"合計 新規 {total_new} 件")


if __name__ == "__main__":
    run_once()
