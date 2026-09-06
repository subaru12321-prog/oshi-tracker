"""
≠ME 公式サイト (https://not-equal-me.jp/) を取得する。

公式APIは存在しないため、公開されているHTMLページをrequests + BeautifulSoupで
直接パースする。サイト側のマークアップ変更で簡単に壊れる想定。

- NEWS一覧 (https://not-equal-me.jp/news/1/) は `ul.infoList > li > a` の並びで
  比較的安定した構造。ただし末尾スラッシュなしのURL
  (https://not-equal-me.jp/news/1) はリダイレクトされるため、必ずスラッシュ付き
  のURLを叩く。また、ブラウザ的なUser-Agentを送らないと弾かれることがあるため
  HEADERSを付与している。
- SCHEDULE (https://not-equal-me.jp/schedule/) はJavaScriptでの非同期取得ではなく
  サーバー側で月間カレンダーがそのままHTMLに描画されているため、同様にrequests +
  BeautifulSoupでパース可能。ただし表示されるのは常に「アクセス時点のデフォルト月」
  のみで、月送りはページ内のJSリンク (`onclick="return send(...)"`) 経由のため
  それ以外の月は取得できない。年月はカレンダーヘッダー(`ul.calendarHeader`)から、
  日はカレンダーセル(`div.cell > span.date`)から取得して組み立てている。
  この構造が変わったり、将来的にJS描画(SPA化など)に変更された場合はすぐに
  取得できなくなるので注意。
"""
import datetime
import re

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://not-equal-me.jp"
NEWS_URL = f"{BASE_URL}/news/1/"
SCHEDULE_URL = f"{BASE_URL}/schedule/"

HEADERS = {"User-Agent": "Mozilla/5.0 (oshi-tracker personal use bot)"}

JST = datetime.timezone(datetime.timedelta(hours=9))

AUTHOR = "≠ME公式サイト"


def _fetch(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def _jst_midnight_to_utc_iso(year, month, day):
    dt = datetime.datetime(year, month, day, 0, 0, 0, tzinfo=JST)
    return dt.astimezone(datetime.timezone.utc).isoformat()


def _make_content(category, title):
    if category:
        return f"【{category}】{title}"
    return title


def _collect_news(limit):
    """NEWS一覧ページを最新limit件までパースする。"""
    html = _fetch(NEWS_URL)
    soup = BeautifulSoup(html, "html.parser")

    results = []
    items = soup.select("ul.infoList > li")
    for li in items:
        if len(results) >= limit:
            break
        try:
            a = li.find("a", href=True)
            if a is None:
                continue
            href = a["href"]
            m = re.search(r"/news/detail/(\d+)", href)
            if not m:
                continue
            news_id = m.group(1)

            date_p = a.select_one("p.date")
            title_p = a.select_one("p.tit")
            title = title_p.get_text(strip=True) if title_p else ""

            category = None
            date_text = ""
            if date_p is not None:
                # p.date の直下は "2026.09.04" というテキストノードで始まり、
                # その後に <span class="catN">カテゴリ名</span> と
                # <span class="new">NEW</span> が続く。"new" 以外のspanが
                # カテゴリ。NEWは日付/カテゴリのどちらにも含めず無視する。
                first_text = date_p.find(string=True, recursive=False)
                date_text = (first_text or "").strip()
                for span in date_p.find_all("span"):
                    classes = span.get("class") or []
                    if "new" in classes:
                        continue
                    category = span.get_text(strip=True)
                    break

            published_at = None
            date_m = re.match(r"(\d{4})\.(\d{2})\.(\d{2})", date_text)
            if date_m:
                y, mo, d = (int(x) for x in date_m.groups())
                published_at = _jst_midnight_to_utc_iso(y, mo, d)
            else:
                published_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

            results.append(
                {
                    "identifier": "news",
                    "platform": "official",
                    "source_id": f"news-{news_id}",
                    "author": AUTHOR,
                    "content": _make_content(category, title),
                    "url": f"{BASE_URL}{href}" if href.startswith("/") else href,
                    "image_url": None,
                    "published_at": published_at,
                }
            )
        except Exception as e:
            print(f"[official] news の取得に失敗: {e}")
            continue
    return results


def _collect_schedule():
    """SCHEDULEページのカレンダー(アクセス時点のデフォルト月のみ)をパースする。"""
    html = _fetch(SCHEDULE_URL)
    soup = BeautifulSoup(html, "html.parser")

    header = soup.select_one("ul.calendarHeader")
    if header is None:
        raise RuntimeError("calendarHeader が見つからない(マークアップ変更の可能性)")

    year_span = header.select_one("span.year")
    month_span = header.select_one("span.month")
    if year_span is None or month_span is None:
        raise RuntimeError("年月要素が見つからない(マークアップ変更の可能性)")
    year = int(year_span.get_text(strip=True))
    month = int(month_span.get_text(strip=True))

    results = []
    cells = soup.select("div.calendarBody div.cell")
    for cell in cells:
        date_span = cell.select_one("span.date")
        day_text = date_span.get_text(strip=True) if date_span else ""
        if not day_text.isdigit():
            # 前後の月の空セル
            continue
        day = int(day_text)

        for a in cell.select("a[href]"):
            try:
                href = a["href"]
                m = re.search(r"/schedule/detail/(\d+)", href)
                if not m:
                    continue
                schedule_id = m.group(1)

                cat_span = a.select_one("span.cat")
                tit_span = a.select_one("span.tit")
                category = cat_span.get_text(strip=True) if cat_span else None
                title = tit_span.get_text(strip=True) if tit_span else ""

                published_at = _jst_midnight_to_utc_iso(year, month, day)

                results.append(
                    {
                        "identifier": "schedule",
                        # スケジュールは「これから起きること」なので published_at が未来日になる。
                        # ニュースと同じ platform にすると新着一覧の先頭に常に居座って
                        # しまうため、別プラットフォーム扱いにして専用タブで見せる。
                        "platform": "schedule",
                        "source_id": f"schedule-{schedule_id}",
                        "author": AUTHOR,
                        "content": _make_content(category, title),
                        "url": f"{BASE_URL}{href}" if href.startswith("/") else href,
                        "image_url": None,
                        "published_at": published_at,
                    }
                )
            except Exception as e:
                print(f"[official] schedule の取得に失敗: {e}")
                continue
    return results


def collect(sections, limit=15):
    """sections: ["news", "schedule"] のようなセクション名のリスト。

    どのセクションで失敗しても他のセクションの取得は継続し、例外は投げない。
    """
    results = []

    if "news" in sections:
        try:
            results.extend(_collect_news(limit))
        except Exception as e:
            print(f"[official] news の取得に失敗: {e}")

    if "schedule" in sections:
        try:
            results.extend(_collect_schedule())
        except Exception as e:
            print(f"[official] schedule の取得に失敗: {e}")

    return results
