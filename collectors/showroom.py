"""
SHOWROOM の配信状況を取得する。

公式APIは公開されていないが、SHOWROOM公式サイトが自身のフロントエンドから
呼んでいる公開JSONエンドポイントを利用する(コミュニティで広く使われている方法)。
仕様変更で壊れる可能性がある。
"""
import datetime

import requests

STATUS_URL = "https://www.showroom-live.com/api/room/status"

HEADERS = {"User-Agent": "Mozilla/5.0 (oshi-tracker personal use bot)"}


def fetch_status(room_url_key):
    resp = requests.get(
        STATUS_URL, params={"room_url_key": room_url_key}, headers=HEADERS, timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def collect(room_url_keys):
    """配信中のルームについて、その配信を1件の投稿として返す。"""
    results = []
    for room_url_key in room_url_keys:
        try:
            status = fetch_status(room_url_key)
        except Exception as e:
            print(f"[showroom] {room_url_key} の取得に失敗: {e}")
            continue

        if not status.get("is_live"):
            continue

        room_id = status.get("room_id")
        live_id = status.get("live_id") or status.get("broadcast_key") or room_id
        started_at = status.get("started_at")
        published_at = (
            datetime.datetime.fromtimestamp(started_at, datetime.timezone.utc).isoformat()
            if started_at
            else datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
        name = status.get("room_name") or room_url_key

        results.append(
            {
                "identifier": room_url_key,
                "platform": "showroom",
                "source_id": f"live-{room_id}-{live_id}",
                "author": name,
                "content": f"{name} が配信中です",
                "url": f"https://www.showroom-live.com/{room_url_key}",
                "image_url": status.get("image_s"),
                "published_at": published_at,
            }
        )
    return results
