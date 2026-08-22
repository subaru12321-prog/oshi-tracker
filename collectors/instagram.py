"""
Instagram の公開投稿を取得する。

instaloader を使い、ログインなしで公開アカウントの投稿一覧を取得する。
Instagram側のBot対策により、頻繁に叩くとレート制限・一時ブロックされることがある。
poll_interval_minutesは短くしすぎないこと。
"""
import instaloader

_loader = None


def _get_loader():
    global _loader
    if _loader is None:
        _loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
        )
    return _loader


def collect(usernames, limit_per_user=5):
    results = []
    loader = _get_loader()
    for username in usernames:
        try:
            profile = instaloader.Profile.from_username(loader.context, username)
            posts = profile.get_posts()
            for i, post in enumerate(posts):
                if i >= limit_per_user:
                    break
                results.append(
                    {
                        "identifier": username,
                        "platform": "instagram",
                        "source_id": post.shortcode,
                        "author": username,
                        "content": (post.caption or "")[:500],
                        "url": f"https://www.instagram.com/p/{post.shortcode}/",
                        "image_url": post.url,
                        "published_at": post.date_utc.isoformat(),
                    }
                )
        except Exception as e:
            print(f"[instagram] @{username} の取得に失敗: {e}")
    return results
