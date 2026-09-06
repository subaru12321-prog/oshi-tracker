import datetime

from flask import Flask, render_template, request

import db

app = Flask(__name__)

JST = datetime.timezone(datetime.timedelta(hours=9))


def _is_upcoming(post, threshold):
    """post の予定日時が threshold 以降かどうか。日時が壊れていれば残す。"""
    raw = post.get("published_at")
    if not raw:
        return True
    try:
        return datetime.datetime.fromisoformat(raw) >= threshold
    except ValueError:
        return True

# 表示順・表示ラベルの単一の定義元。テンプレート側では platform_labels 経由で参照する。
PLATFORM_LABELS = {
    "showroom": "SHOWROOM",
    "official": "公式ニュース",
    "schedule": "スケジュール",
    "youtube": "YouTube",
    "instagram": "Instagram",
    "x": "X",
    "tiktok": "TikTok",
}

PLATFORMS = list(PLATFORM_LABELS)


@app.route("/")
def index():
    platform = request.args.get("platform") or None
    member = request.args.get("member") or None
    posts = db.list_posts(
        platform=platform,
        member=member,
        # 絞り込みなしの「すべて」では、未来日のスケジュールを混ぜない。
        exclude_platforms=None if platform else ["schedule"],
        # スケジュールだけを見るときは、近い予定から並べる。
        ascending=(platform == "schedule"),
    )
    if platform == "schedule":
        # 終わった予定は隠す(公式サイトは今月分をまるごと返してくるため)。
        # published_at はJST0時をUTCに直した値なので、文字列比較ではなく
        # 日時として比較する。
        start_of_today = datetime.datetime.now(JST).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        posts = [p for p in posts if _is_upcoming(p, start_of_today)]
    members = db.list_members()
    return render_template(
        "index.html",
        posts=posts,
        platforms=PLATFORMS,
        platform_labels=PLATFORM_LABELS,
        active_platform=platform,
        members=members,
        active_member=member,
    )


if __name__ == "__main__":
    db.init_db()
    # host="0.0.0.0" にするとスマホなど同じWi-Fi内の他端末からもアクセスできる。
    # ただし認証は無いので、公共Wi-Fiなど他人もいるネットワークでは使わないこと。
    # debug=Trueにすると、エラー発生時に同じネットワーク上の誰でもコード実行可能な
    # デバッグコンソールにアクセスできてしまうため、必ずFalseのままにする。
    app.run(host="0.0.0.0", port=5000, debug=False)
