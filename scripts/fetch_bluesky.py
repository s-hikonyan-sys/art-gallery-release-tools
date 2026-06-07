#!/usr/bin/env python3
"""Bluesky 投稿フェッチスクリプト.

AT Protocol の公開エンドポイントを使用（認証不要）。
指定ハッシュタグの投稿を取得し、画像と本文を抽出する。

出力:
    data/bluesky_raw.json
"""

import json
import sys
import time
from pathlib import Path

import requests

OUTPUT_PATH  = Path("data/bluesky_raw.json")
SEARCH_URL   = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"

HASHTAGS = [
    "#NaraSketch",
    "#NaraJapan",
    "#narasketching",
    "#奈良スケッチ",
]


def fetch_posts(hashtag: str, limit: int = 15) -> list[dict]:
    """指定ハッシュタグの投稿を取得する。"""
    try:
        resp = requests.get(
            SEARCH_URL,
            params={"q": hashtag, "limit": limit},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("posts", [])
    except Exception as exc:
        print(f"[WARN] Bluesky search failed for '{hashtag}': {exc}", file=sys.stderr)
        return []


def extract_images(post: dict) -> list[str]:
    """投稿から画像 URL を抽出する（thumb / fullsize）。"""
    images = []
    embed = post.get("embed") or post.get("record", {}).get("embed", {})
    if not embed:
        return images

    # app.bsky.embed.images
    if embed.get("$type") == "app.bsky.embed.images#view":
        for img in embed.get("images", []):
            url = img.get("fullsize") or img.get("thumb")
            if url:
                images.append(url)

    # app.bsky.embed.recordWithMedia
    media = embed.get("media", {})
    if media.get("$type") == "app.bsky.embed.images#view":
        for img in media.get("images", []):
            url = img.get("fullsize") or img.get("thumb")
            if url:
                images.append(url)

    return images


def build_profile_url(handle: str) -> str:
    return f"https://bsky.app/profile/{handle}"


def main() -> None:
    OUTPUT_PATH.parent.mkdir(exist_ok=True)

    seen_uris: set[str] = set()
    results: list[dict] = []

    for hashtag in HASHTAGS:
        print(f"[INFO] Fetching Bluesky: {hashtag}")
        posts = fetch_posts(hashtag)

        for post in posts:
            uri = post.get("uri", "")
            if not uri or uri in seen_uris:
                continue
            seen_uris.add(uri)

            author  = post.get("author", {})
            record  = post.get("record", {})
            text    = record.get("text", "")
            handle  = author.get("handle", "")
            display = author.get("displayName") or handle
            avatar  = author.get("avatar", "")
            created = record.get("createdAt", "")
            images  = extract_images(post)

            # AT URI → Web URL 変換（at://did:.../app.bsky.feed.post/rkey → /profile/handle/post/rkey）
            rkey      = uri.split("/")[-1]
            post_url  = f"https://bsky.app/profile/{handle}/post/{rkey}" if handle and rkey else ""

            results.append({
                "source":       "bluesky",
                "uri":          uri,
                "url":          post_url,
                "text":         text,
                "author_name":  display,
                "author_handle": handle,
                "author_url":   build_profile_url(handle),
                "avatar":       avatar,
                "images":       images,
                "created_at":   created,
                "fetched_at":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
            print(f"[OK] @{handle}: {text[:60]}{'…' if len(text) > 60 else ''}")

        time.sleep(0.5)

    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[INFO] Saved {len(results)} Bluesky posts → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
