#!/usr/bin/env python3
"""Instagram 投稿フェッチスクリプト.

Google Custom Search API で Instagram 投稿を検索し、
Instagram oEmbed API で埋め込み HTML を取得する。

環境変数（GitHub Actions secrets に登録）:
    GOOGLE_API_KEY       : Google Cloud API キー
    GOOGLE_CX            : Custom Search Engine ID
    FACEBOOK_APP_TOKEN   : App ID|App Secret の形式（例: 123456789|abcdef...）

出力:
    data/instagram_raw.json  （呼び出し元の build_feed.py が読む）
"""

import json
import os
import re
import sys
import time
from pathlib import Path

import requests

GOOGLE_API_KEY     = os.environ["GOOGLE_API_KEY"]
GOOGLE_CX          = os.environ["GOOGLE_CX"]
FACEBOOK_APP_TOKEN = os.environ["FACEBOOK_APP_TOKEN"]   # "APP_ID|APP_SECRET"

OUTPUT_PATH = Path("data/instagram_raw.json")

# 検索するハッシュタグクエリ（Google Custom Search に渡す）
SEARCH_QUERIES = [
    'site:instagram.com "#奈良スケッチ"',
    'site:instagram.com "#NaraSketch"',
    'site:instagram.com "#narasketching"',
]

GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"
OEMBED_URL        = "https://graph.facebook.com/v19.0/instagram_oembed"


def google_search(query: str, num: int = 5) -> list[str]:
    """Google Custom Search で Instagram 投稿 URL を取得する。"""
    params = {
        "key": GOOGLE_API_KEY,
        "cx":  GOOGLE_CX,
        "q":   query,
        "num": num,
    }
    try:
        resp = requests.get(GOOGLE_SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        # instagram.com/p/ または /reel/ の URL だけを抽出
        urls = []
        for item in items:
            link = item.get("link", "")
            if re.search(r"instagram\.com/(p|reel)/[\w-]+", link):
                # クエリパラメータを除去して正規化
                clean = re.sub(r"\?.*$", "", link.rstrip("/")) + "/"
                urls.append(clean)
        return urls
    except Exception as exc:
        print(f"[WARN] Google search failed for '{query}': {exc}", file=sys.stderr)
        return []


def get_oembed(url: str) -> dict | None:
    """Instagram oEmbed API から埋め込み情報を取得する。"""
    params = {
        "url":          url,
        "access_token": FACEBOOK_APP_TOKEN,
        "omitscript":   True,   # Instagram embed JS は1回だけ読み込む
        "maxwidth":     540,
    }
    try:
        resp = requests.get(OEMBED_URL, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        print(f"[WARN] oEmbed {resp.status_code} for {url}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"[WARN] oEmbed request failed for {url}: {exc}", file=sys.stderr)
        return None


def main() -> None:
    OUTPUT_PATH.parent.mkdir(exist_ok=True)

    seen_urls: set[str] = set()
    results: list[dict] = []

    for query in SEARCH_QUERIES:
        print(f"[INFO] Searching: {query}")
        urls = google_search(query)
        for url in urls:
            if url in seen_urls:
                continue
            seen_urls.add(url)

            oembed = get_oembed(url)
            if oembed:
                results.append({
                    "source":      "instagram",
                    "url":         url,
                    "html":        oembed.get("html", ""),
                    "author_name": oembed.get("author_name", ""),
                    "thumbnail":   oembed.get("thumbnail_url", ""),
                    "fetched_at":  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                })
                print(f"[OK] {url} — {oembed.get('author_name')}")
            time.sleep(0.5)   # API レート制限対策

        time.sleep(1)

    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[INFO] Saved {len(results)} Instagram posts → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
