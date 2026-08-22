"""
TikTok の投稿を取得する。

公式APIは投稿監視向けに一般公開されていないため、非公式ライブラリ TikTokApi
(Playwrightでブラウザを操作してTikTok内部APIを叩く) を使う。
ブラウザのCookieから取得した ms_token が必要で、有効期限が切れたら再取得が必要。
利用規約上グレーな手法であり、壊れやすい点に注意。
"""
import asyncio
import datetime

from TikTokApi import TikTokApi

import config


async def _collect_async(usernames, limit_per_user=5):
    if not config.TIKTOK_MS_TOKEN:
        raise RuntimeError(".env に TIKTOK_MS_TOKEN を設定してください。")

    results = []
    async with TikTokApi() as api:
        await api.create_sessions(
            ms_tokens=[config.TIKTOK_MS_TOKEN],
            num_sessions=1,
            sleep_after=3,
            browser="chromium",
        )
        for username in usernames:
            try:
                user = api.user(username=username)
                count = 0
                async for video in user.videos(count=limit_per_user):
                    v = video.as_dict
                    create_time = v.get("createTime")
                    published_at = (
                        datetime.datetime.fromtimestamp(create_time).isoformat()
                        if create_time
                        else None
                    )
                    results.append(
                        {
                            "identifier": username,
                            "platform": "tiktok",
                            "source_id": v.get("id"),
                            "author": username,
                            "content": (v.get("desc") or "")[:500],
                            "url": f"https://www.tiktok.com/@{username}/video/{v.get('id')}",
                            "image_url": v.get("video", {}).get("cover"),
                            "published_at": published_at,
                        }
                    )
                    count += 1
                    if count >= limit_per_user:
                        break
            except Exception as e:
                print(f"[tiktok] @{username} の取得に失敗: {e}")
    return results


def collect(usernames, limit_per_user=5):
    return asyncio.run(_collect_async(usernames, limit_per_user))
