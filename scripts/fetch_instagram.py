#!/usr/bin/env python3
"""Instagram 投稿フェッチスクリプト（instaloader 版）.

instaloader を使ってハッシュタグから投稿を取得する。
Meta API・認証・GitHub Secrets は不要。

出力:
    data/instagram_raw.json  （build_feed.py が読む）
"""

import json
import sys
import time
from pathlib import Path

import instaloader

OUTPUT_PATH = Path("data/instagram_raw.json")
MAX_POSTS_PER_TAG = 10  # タグ1つあたりの取得上限

HASHTAGS = [
    "奈良スケッチ",
    "NaraSketch",
    "narasketching",
]


def fetch_hashtag(loader: instaloader.Instaloader, tag: str, limit: int) -> list[dict]:
    """ハッシュタグから投稿メタデータを取得する。"""
    results = []
    try:
        hashtag = instaloader.Hashtag.from_name(loader.context, tag)
        for post in hashtag.get_posts():
            if len(results) >= limit:
                break
            if post.is_video and not post.video_url:
                continue

            shortcode = post.shortcode
            url = f"https://www.instagram.com/p/{shortcode}/"
            thumbnail = post.url  # 画像 URL（動画の場合はサムネ）

            results.append({
                "source":      "instagram",
                "url":         url,
                "shortcode":   shortcode,
                "caption":     post.caption or "",
                "author_name": post.owner_username,
                "thumbnail":   thumbnail,
                "likes":       post.likes,
                "created_at":  post.date_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fetched_at":  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "tag":         tag,
            })
            time.sleep(1)  # レート制限対策

    except instaloader.exceptions.InstaloaderException as exc:
        print(f"[WARN] instaloader error for #{tag}: {exc}", file=sys.stderr)
    except Exception as exc:
        print(f"[WARN] Unexpected error for #{tag}: {exc}", file=sys.stderr)

    return results


def main() -> None:
    OUTPUT_PATH.parent.mkdir(exist_ok=True)

    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_comments=False,
        save_metadata=False,
        quiet=True,
    )

    seen_urls: set[str] = set()
    all_posts: list[dict] = []

    for tag in HASHTAGS:
        print(f"[INFO] Fetching #{tag} ...")
        posts = fetch_hashtag(loader, tag, MAX_POSTS_PER_TAG)
        for post in posts:
            if post["url"] not in seen_urls:
                seen_urls.add(post["url"])
                all_posts.append(post)
        print(f"[INFO] #{tag}: {len(posts)} posts fetched")
        time.sleep(3)  # タグ間のインターバル

    OUTPUT_PATH.write_text(
        json.dumps(all_posts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[INFO] Saved {len(all_posts)} Instagram posts → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
