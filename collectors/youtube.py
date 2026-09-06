"""
YouTube チャンネルの投稿動画を取得する。

公式APIキーは使わず、YouTubeが各チャンネルに対して公開しているAtomフィード
(`/feeds/videos.xml?channel_id=...`)を利用する。認証不要。

実測メモ: このエンドポイントは同一URLへの連続アクセスでも 404 / 200 / 404 の
ように断続的に失敗することがある(チャンネルが本当に存在しないわけではない)。
そのため404を含む失敗はリトライ対象とし、数回リトライしてから諦める。
"""
import time
import xml.etree.ElementTree as ET

import requests

FEED_URL = "https://www.youtube.com/feeds/videos.xml"

HEADERS = {"User-Agent": "Mozilla/5.0 (oshi-tracker personal use bot)"}

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2

NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def fetch_feed(channel_id):
    """指定チャンネルのAtomフィードを取得する。失敗時は数回リトライする。"""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(
                FEED_URL, params={"channel_id": channel_id}, headers=HEADERS, timeout=15
            )
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
    raise last_error


def parse_feed(xml_text):
    """Atom XMLをパースし、(チャンネル名, entry要素のリスト)を返す。"""
    root = ET.fromstring(xml_text)
    channel_title_el = root.find("atom:title", NAMESPACES)
    channel_title = channel_title_el.text if channel_title_el is not None else None
    entries = root.findall("atom:entry", NAMESPACES)
    return channel_title, entries


def _entry_to_dict(entry, channel_id, channel_title):
    video_id_el = entry.find("yt:videoId", NAMESPACES)
    video_id = video_id_el.text if video_id_el is not None else None

    title_el = entry.find("atom:title", NAMESPACES)
    title = title_el.text if title_el is not None else None

    url = None
    for link_el in entry.findall("atom:link", NAMESPACES):
        if link_el.get("rel") == "alternate":
            url = link_el.get("href")
            break
    if url is None:
        url = f"https://www.youtube.com/watch?v={video_id}"

    published_el = entry.find("atom:published", NAMESPACES)
    published_at = published_el.text if published_el is not None else None

    image_url = None
    media_group = entry.find("media:group", NAMESPACES)
    if media_group is not None:
        thumbnail_el = media_group.find("media:thumbnail", NAMESPACES)
        if thumbnail_el is not None:
            image_url = thumbnail_el.get("url")

    return {
        "identifier": channel_id,
        "platform": "youtube",
        "source_id": video_id,
        "author": channel_title,
        "content": title,
        "url": url,
        "image_url": image_url,
        "published_at": published_at,
    }


def collect(channel_ids, limit_per_channel=5):
    """channel_ids: YouTubeチャンネルIDの文字列リスト"""
    results = []
    for channel_id in channel_ids:
        try:
            xml_text = fetch_feed(channel_id)
            channel_title, entries = parse_feed(xml_text)
        except Exception as e:
            print(f"[youtube] {channel_id} の取得に失敗: {e}")
            continue

        for entry in entries[:limit_per_channel]:
            results.append(_entry_to_dict(entry, channel_id, channel_title))

    return results
