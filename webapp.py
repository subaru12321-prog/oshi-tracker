from flask import Flask, render_template, request

import db

app = Flask(__name__)

PLATFORMS = ["showroom", "instagram", "x", "tiktok"]


@app.route("/")
def index():
    platform = request.args.get("platform") or None
    member = request.args.get("member") or None
    posts = db.list_posts(platform=platform, member=member)
    members = db.list_members()
    return render_template(
        "index.html",
        posts=posts,
        platforms=PLATFORMS,
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
