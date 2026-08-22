"""
X (Twitter) の投稿を取得する。

公式APIの無料枠では実用的な投稿取得ができないため、非公式ライブラリ twikit
(ブラウザと同じGraphQLエンドポイントを叩く) を使う。X本人アカウントでの
ログインが必要で、利用規約上グレーな手法である点に注意。
頻度を上げすぎるとアカウントが制限される可能性がある。
"""
import asyncio
from pathlib import Path

from twikit import Client

import config

COOKIES_PATH = Path(__file__).parent.parent / "cookies.json"


async def _login(client):
    if not (config.X_USERNAME and config.X_EMAIL and config.X_PASSWORD):
        raise RuntimeError(
            ".env に X_USERNAME / X_EMAIL / X_PASSWORD を設定してください。"
        )
    await client.login(
        auth_info_1=config.X_USERNAME,
        auth_info_2=config.X_EMAIL,
        password=config.X_PASSWORD,
    )
    client.save_cookies(str(COOKIES_PATH))


async def _get_client():
    client = Client("ja-JP")
    if COOKIES_PATH.exists():
        client.load_cookies(str(COOKIES_PATH))
    else:
        await _login(client)
    return client


async def _collect_async(usernames, limit_per_user=5):
    results = []
    client = await _get_client()
    for username in usernames:
        try:
            try:
                user = await client.get_user_by_screen_name(username)
            except Exception as e:
                # 保存済みcookieが期限切れ・無効化されている可能性があるので、
                # 1回だけ再ログインして取り直す。
                if not COOKIES_PATH.exists():
                    raise
                print(f"[x] cookieが無効かもしれないため再ログインします: {e}")
                COOKIES_PATH.unlink()
                await _login(client)
                user = await client.get_user_by_screen_name(username)

            tweets = await client.get_user_tweets(user.id, "Tweets", count=limit_per_user)
            for tweet in tweets[:limit_per_user]:
                media = tweet.media[0].media_url if tweet.media else None
                published_at = (
                    tweet.created_at_datetime.isoformat() if tweet.created_at else None
                )
                results.append(
                    {
                        "identifier": username,
                        "platform": "x",
                        "source_id": tweet.id,
                        "author": username,
                        "content": (tweet.text or "")[:500],
                        "url": f"https://x.com/{username}/status/{tweet.id}",
                        "image_url": media,
                        "published_at": published_at,
                    }
                )
        except Exception as e:
            print(f"[x] @{username} の取得に失敗: {e}")
    return results


def collect(usernames, limit_per_user=5):
    return asyncio.run(_collect_async(usernames, limit_per_user))
