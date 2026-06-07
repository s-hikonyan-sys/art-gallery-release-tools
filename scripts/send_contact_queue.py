#!/usr/bin/env python3
"""お問い合わせキューを読み込んで Slack に送信するスクリプト.

GitHub Actions から呼び出される（release-tools の send_contact_queue.yml）。
キューファイルは backend コンテナの /app/contact_queue/ に存在するため、
SSH 経由で VPS から取得して処理する。

環境変数:
    SLACK_CONTACT_WEBHOOK_URL : Slack Incoming Webhook URL（お問い合わせ通知用、release-tools Secrets）
    QUEUE_DIR            : キューファイルのローカルパス（rsync後の一時ディレクトリ）
    DEAD_LETTER_DIR      : 最大リトライ超過ファイルの保存先

動作:
    1. QUEUE_DIR 内の *.json を処理
    2. Slack 送信成功 → ファイルを削除
    3. 送信失敗 → ファイルはそのまま（次回 Actions 実行時に再試行）
    4. 送信成功/失敗の件数をサマリとして stdout に出力
"""

import json
import os
import sys
from pathlib import Path

import requests

SLACK_CONTACT_WEBHOOK_URL = os.environ.get("SLACK_CONTACT_WEBHOOK_URL", "")
QUEUE_DIR         = Path(os.environ.get("QUEUE_DIR", "/tmp/contact_queue"))
REMOVED_LIST_FILE = Path(os.environ.get("REMOVED_LIST_FILE", str(QUEUE_DIR / ".removed_files")))
MAX_RETRIES       = 5
TIMEOUT           = 10

SUBJECT_LABELS = {
    "purchase":   "作品の購入について",
    "exhibit":    "展示・掲載のご依頼",
    "commission": "制作依頼・スケッチ指導",
    "engineer":   "エンジニアとしてのお仕事",
    "other":      "その他",
}


def build_slack_payload(contact: dict) -> dict:
    label = SUBJECT_LABELS.get(contact.get("subject", ""), contact.get("subject", ""))
    queued_at = contact.get("queued_at", "不明")
    return {
        "text": f"📬 お問い合わせが届きました",
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "📬 新しいお問い合わせ", "emoji": True}},
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*お名前*\n{contact.get('name', '')}"},
                    {"type": "mrkdwn", "text": f"*メールアドレス*\n{contact.get('email', '')}"},
                    {"type": "mrkdwn", "text": f"*件名*\n{label}"},
                    {"type": "mrkdwn", "text": f"*受信日時*\n{queued_at}"},
                ],
            },
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*メッセージ*\n{contact.get('message', '')}"}},
        ],
    }


def send_to_slack(contact: dict) -> bool:
    payload = build_slack_payload(contact)
    try:
        resp = requests.post(
            SLACK_CONTACT_WEBHOOK_URL,
            json=payload,
            timeout=TIMEOUT,
            headers={"Content-Type": "application/json"},
        )
        return resp.status_code == 200 and resp.text.strip() == "ok"
    except requests.RequestException as exc:
        print(f"[WARN] Slack request failed: {exc}", file=sys.stderr)
        return False


def main() -> None:
    if not SLACK_CONTACT_WEBHOOK_URL:
        print("[ERROR] SLACK_CONTACT_WEBHOOK_URL is not set.", file=sys.stderr)
        sys.exit(1)

    if not QUEUE_DIR.exists():
        print(f"[INFO] Queue directory not found: {QUEUE_DIR}")
        return

    files = sorted(QUEUE_DIR.glob("*.json"))
    if not files:
        print("[INFO] No queued contacts.")
        return

    print(f"[INFO] Processing {len(files)} queued contact(s).")
    sent_count = 0
    fail_count = 0
    removed_files: list[str] = []

    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[WARN] Cannot read {path.name}: {exc}", file=sys.stderr)
            fail_count += 1
            continue

        retry_count = data.get("retry_count", 0)

        if retry_count >= MAX_RETRIES:
            dead = QUEUE_DIR / "dead_letter" / path.name
            dead.parent.mkdir(exist_ok=True)
            path.rename(dead)
            print(f"[WARN] Max retries reached → dead_letter: {path.name}")
            fail_count += 1
            continue

        if send_to_slack(data):
            path.unlink()
            removed_files.append(path.name)
            print(f"[OK] Sent and removed: {path.name}")
            sent_count += 1
        else:
            data["retry_count"] = retry_count + 1
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[WARN] Failed (retry_count={data['retry_count']}): {path.name}")
            fail_count += 1

    print(f"\n[SUMMARY] sent={sent_count}, failed/skipped={fail_count}")

    if removed_files:
        REMOVED_LIST_FILE.write_text("\n".join(removed_files) + "\n", encoding="utf-8")
        print(f"[INFO] Wrote removed file list: {REMOVED_LIST_FILE}")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
