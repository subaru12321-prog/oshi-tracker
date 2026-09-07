"""
スマホから転送された通知を1件受け取り、DBに保存して docs/data.json に反映する。

GitHub Actions の repository_dispatch イベントから呼ばれる。
ペイロードは環境変数 NOTIFICATION_PAYLOAD にJSON文字列で渡す。

想定するペイロード:
    {"app": "Instagram", "title": "suzuki_hitomi__", "text": "新しい写真を投稿しました"}

Instagram・X・TikTokは、クラウドのIPからはスクレイピングでの取得ができない
(データセンターのIPが遮断されている)。そこで、各アプリが公式に配信している
プッシュ通知をスマホ側で拾って転送してもらい、それを記録する。
"""
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

import config
import db
import export_json
import member_match

DOCS_DATA_JSON_PATH = Path(__file__).parent / "docs" / "data.json"

# 通知元のアプリ名 -> platform名。判定は小文字化した部分一致で行う。
APP_PATTERNS = [
    ("instagram", "instagram"),
    ("tiktok", "tiktok"),
    ("twitter", "x"),
    ("x", "x"),
]

# アプリを開くためのリンク(通知には投稿URLが含まれないため、プロフィールや
# アプリのトップに飛ばすことしかできない)
PLATFORM_URLS = {
    "instagram": "https://www.instagram.com/{author}/",
    "x": "https://x.com/{author}",
    "tiktok": "https://www.tiktok.com/@{author}",
}
# ストーリーズの通知は記録しない。
# 24時間で消えるうえ通知に個別リンクが含まれず、さらにInstagramが複数人分を
# 1通にまとめて送ってくるため先頭の1人にしか紐付けられない。
# 件数のわりに情報として使えないため除外する。
STORY_PATTERNS = ("ストーリーズ", "ストーリー", "stories", "story")

# スマホ側が「通知タイトル ||| 通知本文」の形でつないで送ってくるときの区切り
RAW_SEPARATOR = "|||"

PLATFORM_FALLBACK_URLS = {
    "instagram": "https://www.instagram.com/",
    "x": "https://x.com/",
    "tiktok": "https://www.tiktok.com/",
}


def detect_platform(app_name):
    """アプリ名からplatformを判定する。判定できなければ None。"""
    name = (app_name or "").strip().lower()
    if not name:
        return None
    for pattern, platform in APP_PATTERNS:
        if pattern in name:
            return platform
    return None


def _first_handle_candidate(title):
    """通知タイトルの先頭にあるユーザー名らしき部分を取り出す。

    Instagramは複数人の更新を1通にまとめることがあり、タイトルが
    「honda_miyuki__、他6人」のような形になる。丸ごとユーザー名として
    扱うとリンクが壊れるので、区切り文字より前だけを見る。
    """
    candidate = (title or "").strip()
    for separator in ("、", ",", " と", "・"):
        if separator in candidate:
            candidate = candidate.split(separator)[0]
            break
    return candidate.strip()


def _looks_like_handle(text):
    """Instagramのようにユーザー名がそのまま通知タイトルに入るケースを拾う。

    注意: str.isalnum() は日本語も真を返すため、それだけで判定すると
    「谷崎早耶」のような表示名をユーザー名と誤認して
    https://x.com/谷崎早耶 のような壊れたURLを作ってしまう。ASCIIに限定する。
    """
    candidate = (text or "").strip().lstrip("@")
    if not candidate or len(candidate) > 40:
        return False
    return all(("a" <= c <= "z") or ("A" <= c <= "Z") or c.isdigit() or c in "._-"
               for c in candidate)


def build_handle_map(cfg):
    """(platform, 小文字のユーザー名) -> メンバー名 の対応表を作る。

    通知には日本語の名前ではなくユーザー名だけが入ることが多いため
    (例: Instagramの「suzuki_hitomi__」)、config.yaml のアカウント情報から
    引けるようにしておく。
    """
    mapping = {}
    for m in cfg.get("members", []):
        name = m.get("name")
        if not name:
            continue
        for platform in ("instagram", "x", "tiktok"):
            username = (m.get(platform) or {}).get("username")
            if username:
                mapping[(platform, username.lower())] = name
    return mapping


def build_profile_map(cfg):
    """(platform, メンバー名) -> ユーザー名 の対応表を作る。

    通知に投稿URLが入っていない場合でも、メンバーさえ分かれば
    その人のプロフィールには飛ばせるようにするため。
    """
    mapping = {}
    for m in cfg.get("members", []):
        name = m.get("name")
        if not name:
            continue
        for platform in ("instagram", "x", "tiktok"):
            username = (m.get(platform) or {}).get("username")
            if username:
                mapping[(platform, name)] = username
    return mapping


def build_alias_map(cfg):
    """通知に出てくる表示名 -> メンバー名 の対応表を作る。

    通知のタイトルはユーザー名とは限らず、アプリ上の表示名が入ることがある
    (例: TikTokの「≠ME_official」)。config.yaml の aliases: に書いておくと
    それも手がかりにする。
    """
    mapping = {}
    for m in cfg.get("members", []):
        name = m.get("name")
        if not name:
            continue
        for alias in m.get("aliases") or []:
            mapping[str(alias).strip().lower()] = name
    return mapping


def find_member_for_notification(platform, title, content, handle_map, member_names,
                                 alias_map=None):
    """通知からメンバーを特定する。ユーザー名 -> 日本語名の順で試す。"""
    handle = _first_handle_candidate(title).lstrip("@").lower()
    if handle:
        matched = handle_map.get((platform, handle))
        if matched:
            return matched
        matched = (alias_map or {}).get(handle)
        if matched:
            return matched

    # タイトル全体が表示名になっていることもある
    matched = (alias_map or {}).get((title or "").strip().lower())
    if matched:
        return matched

    lowered = (content or "").lower()
    for (mapped_platform, username), name in handle_map.items():
        if mapped_platform == platform and username in lowered:
            return name

    return member_match.find_member(content, member_names)


def build_post(payload, member_names, handle_map, alias_map=None, profile_map=None):
    """通知のペイロードから、DBに入れる1件分のdictを組み立てる。"""
    platform = detect_platform(payload.get("app"))
    if not platform:
        raise ValueError(f"対応していないアプリからの通知です: {payload.get('app')!r}")

    # スマホ側は、通知のタイトルと本文を区切り文字でつないだ1つの文字列
    # (raw)として送ってくる。通知の文面に引用符や改行が含まれるとJSONが
    # 壊れてGitHubに 400 で弾かれるため、送信前にまとめて危険な文字を
    # 取り除いてもらう都合でこの形にしている。
    # title/text を個別に送る旧形式も引き続き受け付ける。
    raw = payload.get("raw")
    if raw is not None:
        parts = str(raw).split(RAW_SEPARATOR, 1)
        title = parts[0].strip()
        text = parts[1].strip() if len(parts) > 1 else ""
    else:
        title = (payload.get("title") or "").strip()
        text = (payload.get("text") or "").strip()

    content = " ".join(part for part in (title, text) if part)
    if not content:
        raise ValueError("通知の本文が空です")

    author = title or platform
    lowered = content.lower()
    if any(pattern.lower() in lowered for pattern in STORY_PATTERNS):
        raise ValueError("ストーリーズの通知は記録しない設定です")

    member = find_member_for_notification(
        platform, title, content, handle_map, member_names, alias_map
    )
    # 【重要】メンバーだと特定できない通知は記録しない。
    # Instagram等はDM・いいね・コメントの通知も送ってくるため、
    # 素通しすると私信の内容が公開ページに載ってしまう。
    # config.yaml に載っているアカウント由来のものだけを通す。
    if not member:
        raise ValueError(
            "どのメンバーの通知か特定できませんでした(DMや他人の通知の可能性が"
            "あるため、公開ページには記録しません)"
        )

    # リンク先は「投稿元(本人のプロフィール)」に統一する。
    #   1. 特定できたメンバーのプロフィール(config.yamlのユーザー名を使う)
    #   2. 通知タイトルがユーザー名そのものなら、それを使う
    #   3. アプリのトップページ
    #
    # 以前は通知本文からURLを拾って投稿への直リンクにしていたが、
    # 日本語には単語の区切りに空白が無いため、URLの後ろに続く本文まで
    # まとめてURLとして拾ってしまい、開けないリンクが量産された。
    # X・Instagramはそもそも通知に投稿IDを含まないので直リンクは作れない。
    # プロフィールに飛べれば最新の投稿は見られるため、確実な方を選ぶ。
    handle = _first_handle_candidate(title)
    profile_handle = (profile_map or {}).get((platform, member))
    if profile_handle:
        url = PLATFORM_URLS[platform].format(author=profile_handle)
    elif _looks_like_handle(handle):
        url = PLATFORM_URLS[platform].format(author=handle.lstrip("@"))
    else:
        url = PLATFORM_FALLBACK_URLS[platform]

    received_at = payload.get("time")
    if received_at:
        try:
            published_at = datetime.datetime.fromisoformat(received_at).isoformat()
        except ValueError:
            published_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    else:
        published_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 同じ通知が二重に飛んできても増えないよう、内容と日付からIDを作る。
    # (同じ文面の通知が同じ日に2回来ることはまずないという前提)
    day = published_at[:10]
    digest = hashlib.sha1(f"{platform}|{content}|{day}".encode("utf-8")).hexdigest()

    return {
        "platform": platform,
        "source_id": f"notif-{digest[:16]}",
        "author": author,
        "content": content,
        "url": url,
        "image_url": None,
        "published_at": published_at,
        "member": member,
    }


def main():
    raw = os.environ.get("NOTIFICATION_PAYLOAD", "").strip()
    if not raw:
        print("NOTIFICATION_PAYLOAD が空です", file=sys.stderr)
        return 1

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        # 通知の文面に引用符や改行が含まれるとJSONが壊れることがある。
        print(f"ペイロードのJSONを解釈できませんでした: {e}", file=sys.stderr)
        return 1

    cfg = config.load_config()
    member_names = [m["name"] for m in cfg.get("members", []) if m.get("name")]
    handle_map = build_handle_map(cfg)
    alias_map = build_alias_map(cfg)
    profile_map = build_profile_map(cfg)

    try:
        post = build_post(payload, member_names, handle_map, alias_map, profile_map)
    except ValueError as e:
        # 対象外の通知(DM・いいね・他アプリ等)を弾くのは正常な動作なので、
        # ワークフローを失敗扱いにしない。失敗にするとGitHubから毎回
        # 「実行に失敗しました」というメールが届いてしまう。
        print(f"この通知は記録対象外なのでスキップしました: {e}")
        return 0

    db.init_db()
    db.import_from_json(DOCS_DATA_JSON_PATH)

    if db.insert_post(**post):
        print(f"[{post['platform']}] {post['content'][:60]} を記録しました")
    else:
        print("同じ通知が既に記録されているため、何もしませんでした")

    export_json.export()
    return 0


if __name__ == "__main__":
    sys.exit(main())
