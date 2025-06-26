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
from ml_keywords import ML_KEYWORDS, MATERIAL_KEYWORDS, LLM_KEYWORDS

# ArXiv APIのURL
ARXIV_API_BASE = "http://export.arxiv.org/api/query?"

# 検索対象のカテゴリと対応するキーワード
SEARCH_CATEGORIES = {
    "cond-mat.mtrl-sci": ML_KEYWORDS,  # 物性・材料科学では機械学習キーワードでフィルタ
    "cs.AI": MATERIAL_KEYWORDS,  # CS.AIでは材料キーワードでフィルタ
    "cs.LG": MATERIAL_KEYWORDS,  # CS.LGでは材料キーワードでフィルタ
    "cs.CL": MATERIAL_KEYWORDS,  # CS.CLでは材料キーワードでフィルタ
    # LLM関連の論文を取得するための追加カテゴリ
    "cs.AI-LLM": LLM_KEYWORDS,  # CS.AIからLLM関連論文
    "cs.LG-LLM": LLM_KEYWORDS,  # CS.LGからLLM関連論文
    "cs.CL-LLM": LLM_KEYWORDS,  # CS.CLからLLM関連論文
}

WEBHOOK = os.environ.get("SLACK_WEBHOOK_URL")
LLM_WEBHOOK = os.environ.get("SLACK_LLM_WEBHOOK_URL")


def fetch_new_entries_for_category(category: str, keywords: list):
    """指定カテゴリから新しいエントリを取得"""
    try:
        # 現在のUTC時刻を取得
        now = datetime.datetime.utcnow()
        # 28時間前に変更（EST/EDTとの時差を考慮）
        time_threshold = now - timedelta(hours=28)

        print(f"Current UTC time: {now}")
        print(f"Time threshold (28h ago): {time_threshold}")

        # キーワードでabstractフィルタを構築
        keyword_terms = [f'abs:"{keyword}"' for keyword in keywords]
        keyword_filter = " OR ".join(keyword_terms)

        # LLM専用カテゴリの場合、実際のarXivカテゴリ名を使用
        actual_category = category
        if category.endswith("-LLM"):
            actual_category = category.replace("-LLM", "")

        # カテゴリとキーワードを組み合わせた検索クエリ
        search_query = f"cat:{actual_category} AND ({keyword_filter})"

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

        print(f"Fetching from {category} (actual: {actual_category}): {url}")

        # フィードをパース
        feed = feedparser.parse(url)

        new_entries = []
        for entry in feed.entries:
            # 'published' フィールドの日付を解析
            published_str = entry.published
            published = datetime.datetime.strptime(published_str, "%Y-%m-%dT%H:%M:%SZ")

            # デバッグ用ログ
            print(
                f"Paper: {entry.title[:50]}... | Published: {published} | Include: {published >= time_threshold}"
            )

            # 指定時間内に公開されたものかを確認
            if published >= time_threshold:
                new_entries.append(entry)

        print(
            f"Total entries found: {len(feed.entries)}, New entries: {len(new_entries)}"
        )

        # APIレート制限を考慮して少し待機
        time.sleep(1)

        # 古い順に並べ替えて返す
        return list(reversed(new_entries))

    except Exception as e:
        print(f"Error fetching entries for {category}: {e}")
        return []


def get_category_emoji(category: str) -> str:
    """カテゴリに対応する絵文字を返す"""
    emoji_map = {
        "cond-mat.mtrl-sci": "🔬",
        "cs.AI": "🤖",
        "cs.LG": "📊",
        "cs.CL": "💬",
        # LLM専用カテゴリ用の絵文字
        "cs.AI-LLM": "🧠",
        "cs.LG-LLM": "🤖💬",
        "cs.CL-LLM": "📝",
    }
    return emoji_map.get(category, "📄")


def build_message_for_category(category: str, entries: list) -> str:
    """指定カテゴリのSlack用メッセージ文字列組み立て"""
    if not entries:
        return ""

    emoji = get_category_emoji(category)
    lines = [f"{emoji} *{category} 新着論文 ({len(entries)}件)*"]

    for e in entries:
        title = e.title.replace("\n", " ")
        # abstractページのリンクを使用
        abs_url = e.link  # デフォルトでabstractページのURL

        # カテゴリ情報を取得
        categories = (
            ", ".join(tag["term"] for tag in e.tags) if hasattr(e, "tags") else category
        )

        lines.append(f"• *{title}*")
        lines.append(f"  📄 <{abs_url}|Abstract> | 🏷️ {categories}")
        lines.append("")  # 空行で区切り

    return "\n".join(lines)


def is_llm_category(category: str) -> bool:
    """LLM関連カテゴリかどうかを判定"""
    return category.endswith("-LLM")


def post_to_slack(text: str, is_llm: bool = False):
    """Webhook でポスト"""
    webhook_url = LLM_WEBHOOK if is_llm else WEBHOOK
    webhook_name = "SLACK_LLM_WEBHOOK_URL" if is_llm else "SLACK_WEBHOOK_URL"

    if not webhook_url:
        print(f"{webhook_name} environment variable is not set")
        return

    try:
        resp = requests.post(webhook_url, json={"text": text})
        resp.raise_for_status()
        channel_type = "LLM channel" if is_llm else "main channel"
        print(f"Successfully posted to Slack ({channel_type})")
    except Exception as e:
        print(f"Error posting to Slack: {e}")


if __name__ == "__main__":
    all_messages = []
    llm_messages = []

    # 現在の日付を取得（JST）
    jst = datetime.timezone(datetime.timedelta(hours=9))
    current_date = datetime.datetime.now(jst).strftime("%m/%d")

    # 各カテゴリから論文を取得
    for category, keywords in SEARCH_CATEGORIES.items():
        print(f"Processing category: {category}")
        entries = fetch_new_entries_for_category(category, keywords)
        print(f"Found {len(entries)} entries for {category}")

        if entries:
            # メッセージを作成
            message = build_message_for_category(category, entries)
            if message:
                # LLM関連かどうかで分ける
                if is_llm_category(category):
                    llm_messages.append(message)
                else:
                    all_messages.append(message)

    # 通常のメッセージを送信
    if all_messages:
        final_message = f"📅 *arXiv更新情報 ({current_date})*\n\n" + "\n\n".join(
            all_messages
        )
        print(f"Main channel message: {final_message}")
        post_to_slack(final_message)
    else:
        no_papers_message = f"📅 *arXiv更新情報 ({current_date})*\n📚 過去24時間以内に新着論文がありません。"
        print(f"Main channel message: {no_papers_message}")
        post_to_slack(no_papers_message)

    # LLM関連のメッセージを送信
    if llm_messages:
        llm_final_message = (
            f"📅 *arXiv LLM関連更新情報 ({current_date})*\n\n"
            + "\n\n".join(llm_messages)
        )
        print(f"LLM channel message: {llm_final_message}")
        post_to_slack(llm_final_message, is_llm=True)
    else:
        no_llm_papers_message = f"📅 *arXiv LLM関連更新情報 ({current_date})*\n📚 過去24時間以内にLLM関連の新着論文がありません。"
        print(f"LLM channel message: {no_llm_papers_message}")
        post_to_slack(no_llm_papers_message, is_llm=True)
