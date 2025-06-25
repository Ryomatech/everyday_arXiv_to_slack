#!/usr/bin/env python3
# arxiv_to_slack.py
import os
import feedparser
import datetime
import json
import requests
import pathlib

ARXIV_RSS = "https://export.arxiv.org/rss/cond-mat.mtrl-sci"
WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL")
STATE_FILE = pathlib.Path("/tmp/arxiv_condmat_slack.state")  # Docker環境用のパス


def load_last_id() -> str | None:
    """前回送信済みの最上位 arXiv ID を取得"""
    return STATE_FILE.read_text().strip() if STATE_FILE.exists() else None


def save_last_id(arxiv_id: str) -> None:
    """今回送った最新 arXiv ID を保存"""
    STATE_FILE.write_text(arxiv_id)


def fetch_new_entries():
    """RSS からまだ通知していないエントリだけを抽出（新しい順 → 古い順に返す）"""
    try:
        feed = feedparser.parse(ARXIV_RSS)
        last_id = load_last_id()
        new = []

        for entry in feed.entries:  # RSS は新しい順
            aid = entry.link.rsplit("/", 1)[-1]  # arXiv ID
            if aid == last_id:
                break  # ここまでが既読
            new.append(entry)

        if new:  # 先頭 (= 最新) の ID を記録
            save_last_id(new[0].link.rsplit("/", 1)[-1])

        return list(reversed(new))  # 古い順に並べ替えて返す
    except Exception as e:
        print(f"Error fetching entries: {e}")
        return []


def build_message(entries) -> str:
    """Slack 用メッセージ文字列組み立て"""
    if not entries:
        return "🎓 cond-mat.mtrl-sci: きょうは新着論文がありません。"

    lines = ["🎓 *本日の cond-mat.mtrl-sci 新着論文*"]
    for e in entries:
        title = e.title.replace("\n", " ")
        lines.append(f"• <{e.link}|{title}>")

    return "\n".join(lines)


def post_to_slack(text: str):
    """Webhook でポスト"""
    if not WEBHOOK:
        print("SLACK_WEBHOOK_URL environment variable is not set")
        return

    try:
        resp = requests.post(WEBHOOK, json={"text": text})
        resp.raise_for_status()
        print("Successfully posted to Slack")
    except Exception as e:
        print(f"Error posting to Slack: {e}")


if __name__ == "__main__":
    entries = fetch_new_entries()
    message = build_message(entries)
    print(f"Message: {message}")
    post_to_slack(message)
