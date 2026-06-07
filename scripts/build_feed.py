#!/usr/bin/env python3
"""ソーシャルフィード JSON ビルダー.

Instagram + Bluesky の生データを統合し、
フロントエンドが読む social_feed.json を生成する。

出力:
    dist/social_feed.json   （Nginx で公開するディレクトリ）
"""

import json
import time
from pathlib import Path

INSTAGRAM_RAW = Path("data/instagram_raw.json")
BLUESKY_RAW   = Path("data/bluesky_raw.json")
OUTPUT_PATH   = Path("dist/social_feed.json")

# 最大取得件数（Instagram + Bluesky 合計でのキャップ）
MAX_INSTAGRAM = 12
MAX_BLUESKY   = 15


def load_json(path: Path) -> list:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[WARN] Cannot read {path}: {exc}")
        return []


def normalize_instagram(items: list) -> list:
    """Instagram oEmbed データを統一フォーマットに変換する。"""
    result = []
    for item in items[:MAX_INSTAGRAM]:
        if not item.get("html"):
            continue
        result.append({
            "source":      "instagram",
            "type":        "oembed",
            "html":        item["html"],
            "author_name": item.get("author_name", ""),
            "url":         item.get("url", ""),
            "thumbnail":   item.get("thumbnail", ""),
            "fetched_at":  item.get("fetched_at", ""),
        })
    return result


def normalize_bluesky(items: list) -> list:
    """Bluesky の投稿データを統一フォーマットに変換する。"""
    result = []
    for item in items[:MAX_BLUESKY]:
        result.append({
            "source":        "bluesky",
            "type":          "native",
            "text":          item.get("text", ""),
            "author_name":   item.get("author_name", ""),
            "author_handle": item.get("author_handle", ""),
            "author_url":    item.get("author_url", ""),
            "avatar":        item.get("avatar", ""),
            "images":        item.get("images", []),
            "url":           item.get("url", ""),
            "created_at":    item.get("created_at", ""),
            "fetched_at":    item.get("fetched_at", ""),
        })
    return result


def main() -> None:
    OUTPUT_PATH.parent.mkdir(exist_ok=True)

    instagram_posts = normalize_instagram(load_json(INSTAGRAM_RAW))
    bluesky_posts   = normalize_bluesky(load_json(BLUESKY_RAW))

    feed = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "instagram":    instagram_posts,
        "bluesky":      bluesky_posts,
        "hashtags": {
            "ja": ["#奈良スケッチ", "#奈良市", "#大和郡山市", "#桜井市", "#宇陀市",
                   "#天理市", "#橿原市", "#生駒市", "#吉野町", "#明日香村"],
            "en": ["#NaraSketch", "#NaraJapan", "#narasketching",
                   "#NaraCity", "#YamatoKoriyama", "#Sakurai", "#Tenri",
                   "#Kashihara", "#Yoshino", "#Asuka"],
        },
    }

    OUTPUT_PATH.write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[INFO] Generated {OUTPUT_PATH}")
    print(f"       Instagram: {len(instagram_posts)}, Bluesky: {len(bluesky_posts)}")


if __name__ == "__main__":
    main()
