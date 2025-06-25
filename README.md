# arXiv to Slack 自動投稿システム

cond-mat.mtrl-sci カテゴリの新着論文を毎日SlackにポストするGitHub Actionsプロジェクトです。

## 機能

- arXiv RSS (cond-mat.mtrl-sci) から新着論文を取得
- 重複防止機能付き（前回投稿した論文IDを記録）
- 毎日自動実行（日本時間 9:00）
- Docker コンテナで実行

## セットアップ手順

### 1. Slack Webhook URLの取得

1. Slack ワークスペースで新しいアプリを作成
2. Incoming Webhooks を有効化
3. Webhook URL を取得

### 2. 環境変数の設定

#### GitHub Actions で実行する場合（推奨）

リポジトリの Settings > Secrets and variables > Actions から以下を追加：

- `SLACK_WEBHOOK_URL`: 取得したSlack Webhook URL

#### ローカル開発の場合

1. `.env.example` を `.env` にコピー
2. `.env` ファイルに実際のWebhook URLを設定

```bash
cp .env.example .env
# .env ファイルを編集してWebhook URLを設定
```

**重要**: `.env` ファイルは `.gitignore` で除外されているため、GitHubにアップロードされません。

### 3. 実行スケジュール

- **自動実行**: 毎日 UTC 0:00 (日本時間 9:00)
- **手動実行**: GitHub Actions の "Run workflow" ボタンから実行可能

## セキュリティについて

このプロジェクトでは以下の方法でAPIキーを安全に管理しています：

1. **GitHub Secrets**: 本番環境では GitHub の暗号化されたシークレット機能を使用
2. **環境変数**: コードにAPIキーを直接記述しない
3. **`.gitignore`**: 機密情報を含む `.env` ファイルをGitから除外
4. **`.env.example`**: 設定例を提供（実際の値は含まない）

## ローカルでのテスト

```bash
# 依存関係をインストール
pip install -r requirements.txt

# 環境変数を設定して実行
python arxiv_to_slack.py

# または Dockerを使用
docker build -t arxiv-slack .
docker run --rm -e SLACK_WEBHOOK_URL="your_webhook_url_here" arxiv-slack
```

## ファイル構成

```
.
├── arxiv_to_slack.py       # メインスクリプト
├── Dockerfile              # Docker設定
├── requirements.txt        # Python依存関係
├── .env.example           # 環境変数設定例
├── .gitignore             # Git除外設定
├── .github/workflows/
│   └── daily-arxiv.yml     # GitHub Actionsワークフロー
└── README.md               # このファイル
```

## カスタマイズ

### 異なるarXivカテゴリを使用する場合

`arxiv_to_slack.py` の `ARXIV_RSS` 変数を変更してください：

```python
# 例：物理学全般
ARXIV_RSS = "https://export.arxiv.org/rss/physics"

# 例：コンピュータサイエンス
ARXIV_RSS = "https://export.arxiv.org/rss/cs"
```

### 実行時間を変更する場合

`.github/workflows/daily-arxiv.yml` の cron 設定を変更してください：

```yaml
# 毎日 UTC 12:00 (日本時間 21:00) に実行
- cron: '0 12 * * *'
```
