"""
テキスト(ニュースのタイトルや動画のタイトル)から、どのメンバーの話題かを判定する。

SHOWROOMやInstagramのように「アカウント = メンバー」が確定しているソースと違い、
公式サイトのニュースやYouTubeの動画は、どのメンバーの話題かがタイトルの中にしか
書かれていない。そこで名前の部分一致で拾う。

表記ゆれ対策として、比較前に空白を取り除く:
  「尾木 波菜（≠ME）」 -> 「尾木波菜（≠ME）」なので「尾木波菜」と一致する
  「#冨田菜々風」       -> そのまま「冨田菜々風」と一致する
"""
import re

# 全角・半角スペースなどをまとめて除去するための正規表現
_SPACE_RE = re.compile(r"[\s　]+")


def _normalize(text):
    return _SPACE_RE.sub("", text or "")


def find_member(text, member_names):
    """
    text の中に含まれるメンバー名を1つ返す。見つからなければ None。

    複数のメンバー名が含まれる場合は、テキスト中で最初に登場したものを返す
    (グループ全体の話題なら、どのメンバーにも紐付けないほうが自然なため
     呼び出し側で None のまま扱ってよい)。
    """
    normalized_text = _normalize(text)
    if not normalized_text:
        return None

    best_name = None
    best_position = None

    for name in member_names:
        normalized_name = _normalize(name)
        if not normalized_name:
            continue
        position = normalized_text.find(normalized_name)
        if position == -1:
            continue
        if best_position is None or position < best_position:
            best_position = position
            best_name = name

    return best_name
