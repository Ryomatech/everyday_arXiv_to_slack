#!/usr/bin/env python3
# arxiv_to_slack.py
import os
import feedparser
import datetime
from datetime import timedelta
import json
import requests
import pathlib
import urllib.parse
import time
from ml_keywords import ML_KEYWORDS

# ArXiv APIのURL（cond-mat.mtrl-sciカテゴリ）
ARXIV_API_BASE = "http://export.arxiv.org/api/query?"
ARXIV_CATEGORY = "cat:cond-mat.mtrl-sci"

WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL")
STATE_FILE = pathlib.Path("/tmp/arxiv_condmat_slack.state")  # Docker環境用のパス


def load_last_id() -> str | None:
    """前回送信済みの最上位 arXiv ID を取得"""
    return STATE_FILE.read_text().strip() if STATE_FILE.exists() else None


def save_last_id(arxiv_id: str) -> None:
    """今回送った最新 arXiv ID を保存"""
    STATE_FILE.write_text(arxiv_id)


def fetch_new_entries():
    """ArXiv APIから指定時間内の新しいエントリを取得"""
    try:
        # 現在のUTC時刻を取得
        now = datetime.datetime.utcnow()

        # 12時間前のUTC時刻を取得（12時間おきの実行に対応）
        time_threshold = now - timedelta(hours=12)

        # 機械学習関連キーワードでabstractフィルタを構築
        keyword_terms = [f'abs:"{keyword}"' for keyword in ML_KEYWORDS]
        keyword_filter = " OR ".join(keyword_terms)

        # カテゴリと機械学習キーワードを組み合わせた検索クエリ
        search_query = f"{ARXIV_CATEGORY} AND ({keyword_filter})"

        # APIパラメータの設定
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": 300,  # 必要に応じて調整
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        # パラメータをURLエンコードしてクエリ文字列を作成
        query_string = urllib.parse.urlencode(params, safe=":")

        # 完全なAPIリクエストURLを構築
        url = ARXIV_API_BASE + query_string

        # フィードをパース
        feed = feedparser.parse(url)

        new_entries = []
        last_id = load_last_id()

        for entry in feed.entries:
            # arXiv IDを取得
            arxiv_id = entry.id.split("/abs/")[-1]

            # 既に処理済みの論文かチェック
            if arxiv_id == last_id:
                break

            # 'published' フィールドの日付を解析
            published_str = entry.published
            published = datetime.datetime.strptime(published_str, "%Y-%m-%dT%H:%M:%SZ")

            # 指定時間内に公開されたものかを確認
            if published >= time_threshold:
                new_entries.append(entry)

        # 新しいエントリがある場合、最新のIDを保存
        if new_entries:
            latest_id = new_entries[0].id.split("/abs/")[-1]
            save_last_id(latest_id)

        # 古い順に並べ替えて返す
        return list(reversed(new_entries))

    except Exception as e:
        print(f"Error fetching entries: {e}")
        return []


def build_message(entries) -> str:
    """Slack 用メッセージ文字列組み立て"""
    if not entries:
        return "🎓 cond-mat.mtrl-sci: 過去12時間以内に新着論文がありません。"

    lines = [f"🎓 *cond-mat.mtrl-sci 新着論文 ({len(entries)}件)*"]
    for e in entries:
        title = e.title.replace("\n", " ")
        # PDFリンクを取得
        pdf_url = e.link  # デフォルトはabsページ
        for link in e.links:
            if hasattr(link, "title") and link.title == "pdf":
                pdf_url = link.href
                break

        # カテゴリ情報を取得
        categories = (
            ", ".join(tag["term"] for tag in e.tags)
            if hasattr(e, "tags")
            else "cond-mat.mtrl-sci"
        )

        lines.append(f"• *{title}*")
        lines.append(f"  📄 <{pdf_url}|PDF> | 🏷️ {categories}")
        lines.append("")  # 空行で区切り

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
