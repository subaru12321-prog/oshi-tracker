"""
ホーム画面用のアイコン画像を生成する。

デザインは「≠」をダッシュボードと同じ配色(暗い背景 + ピンク)で描いたもの。
色やサイズを変えたい場合はこのファイルの定数を書き換えて実行し直す:
    python tools/make_icons.py

Androidはアイコンを円や角丸に切り抜くことがあるため、背景は全面に敷き、
文字は中央8割の「安全な範囲」に収めている。
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).parent.parent / "docs"

BACKGROUND = "#12141a"
ACCENT = "#ff6fa3"

# 実際に書き出すサイズ
SIZES = {
    "icon-512.png": 512,
    "icon-192.png": 192,
    "apple-touch-icon.png": 180,
    "favicon.png": 64,
}

# 描画は4倍で行ってから縮小し、輪郭をなめらかにする
SUPERSAMPLE = 4
BASE = 512


def draw_icon():
    size = BASE * SUPERSAMPLE
    img = Image.new("RGB", (size, size), BACKGROUND)
    draw = ImageDraw.Draw(img)

    def s(value):
        """512基準の座標を、実際の描画サイズに拡大する。"""
        return value * SUPERSAMPLE

    bar_left, bar_right = s(146), s(366)
    bar_height = s(36)
    radius = bar_height / 2

    # 「=」の2本の横棒
    for center_y in (s(212), s(300)):
        draw.rounded_rectangle(
            [bar_left, center_y - bar_height / 2, bar_right, center_y + bar_height / 2],
            radius=radius,
            fill=ACCENT,
        )

    # 打ち消しの斜線
    draw.line(
        [(s(206), s(346)), (s(306), s(166))],
        fill=ACCENT,
        width=int(bar_height),
    )

    return img


def main():
    master = draw_icon()
    for filename, size in SIZES.items():
        master.resize((size, size), Image.LANCZOS).save(OUT_DIR / filename)
        print(f"{filename} ({size}x{size}) を書き出しました")


if __name__ == "__main__":
    main()
