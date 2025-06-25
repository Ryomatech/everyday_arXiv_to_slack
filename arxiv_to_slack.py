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
from ml_keywords import ML_KEYWORDS, MATERIAL_KEYWORDS

# ArXiv APIのURL
ARXIV_API_BASE = "http://export.arxiv.org/api/query?"

# 検索対象のカテゴリと対応するキーワード
SEARCH_CATEGORIES = {
    "cond-mat.mtrl-sci": ML_KEYWORDS,  # 物性・材料科学では機械学習キーワードでフィルタ
    "cs.AI": MATERIAL_KEYWORDS,  # CS.AIでは材料キーワードでフィルタ
    "cs.LG": MATERIAL_KEYWORDS,  # CS.LGでは材料キーワードでフィルタ
    "cs.CL": MATERIAL_KEYWORDS,  # CS.CLでは材料キーワードでフィルタ
}

WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL")
STATE_FILE = pathlib.Path("/tmp/arxiv_multi_category_slack.state")


def load_last_ids() -> dict:
    """前回送信済みの各カテゴリの最上位 arXiv ID を取得"""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            return {}
    return {}


def save_last_ids(last_ids: dict) -> None:
    """今回送った各カテゴリの最新 arXiv ID を保存"""
    STATE_FILE.write_text(json.dumps(last_ids))


def fetch_new_entries_for_category(category: str, keywords: list):
    """指定カテゴリから新しいエントリを取得"""
    try:
        # 現在のUTC時刻を取得
        now = datetime.datetime.utcnow()
        # 12時間前のUTC時刻を取得
        time_threshold = now - timedelta(hours=12)

        # キーワードでabstractフィルタを構築
        keyword_terms = [f'abs:"{keyword}"' for keyword in keywords]
        keyword_filter = " OR ".join(keyword_terms)

        # カテゴリとキーワードを組み合わせた検索クエリ
        search_query = f"cat:{category} AND ({keyword_filter})"

        # APIパラメータの設定
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": 100,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        # パラメータをURLエンコードしてクエリ文字列を作成
        query_string = urllib.parse.urlencode(params, safe=":")
        url = ARXIV_API_BASE + query_string

        print(f"Fetching from {category}: {url}")

        # フィードをパース
        feed = feedparser.parse(url)

        new_entries = []
        last_ids = load_last_ids()
        last_id = last_ids.get(category)
        print(feed.entries)
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

        # APIレート制限を考慮して少し待機
        time.sleep(1)

        # 古い順に並べ替えて返す
        return list(reversed(new_entries))

    except Exception as e:
        print(f"Error fetching entries for {category}: {e}")
        return []


def get_category_emoji(category: str) -> str:
    """カテゴリに対応する絵文字を返す"""
    emoji_map = {"cond-mat.mtrl-sci": "🔬", "cs.AI": "🤖", "cs.LG": "📊", "cs.CL": "💬"}
    return emoji_map.get(category, "📄")


def build_message_for_category(category: str, entries: list) -> str:
    """指定カテゴリのSlack用メッセージ文字列組み立て"""
    if not entries:
        return ""

    emoji = get_category_emoji(category)
    lines = [f"{emoji} *{category} 新着論文 ({len(entries)}件)*"]

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
            ", ".join(tag["term"] for tag in e.tags) if hasattr(e, "tags") else category
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
    all_messages = []
    last_ids = load_last_ids()

    # 現在の日付を取得（JST）
    jst = datetime.timezone(datetime.timedelta(hours=9))
    current_date = datetime.datetime.now(jst).strftime("%m/%d")

    # 各カテゴリから論文を取得
    for category, keywords in SEARCH_CATEGORIES.items():
        print(f"Processing category: {category}")
        entries = fetch_new_entries_for_category(category, keywords)
        print(entries)
        if entries:
            # 最新のIDを記録
            latest_id = entries[-1].id.split("/abs/")[-1]
            last_ids[category] = latest_id

            # メッセージを作成
            message = build_message_for_category(category, entries)
            if message:
                all_messages.append(message)

    # 最新IDを保存
    save_last_ids(last_ids)

    # すべてのメッセージを結合して送信
    if all_messages:
        final_message = f"📅 *arXiv更新情報 ({current_date})*\n\n" + "\n\n".join(
            all_messages
        )
        print(f"Message: {final_message}")
        post_to_slack(final_message)
    else:
        no_papers_message = f"📅 *arXiv更新情報 ({current_date})*\n📚 過去12時間以内に新着論文がありません。"
        print(f"Message: {no_papers_message}")
        post_to_slack(no_papers_message)
