# arXiv to Slack 自動投稿システム

cond-mat.mtrl-sci カテゴリの新着論文を12時間おきにSlackにポストするGitHub Actionsプロジェクトです。

## 機能

- arXiv API (cond-mat.mtrl-sci) から新着論文を取得
- 時間フィルタリング機能（過去12時間以内の論文のみ取得）
- 重複防止機能付き（前回投稿した論文IDを記録）
- 12時間おき自動実行（日本時間 9:00 と 21:00）
- Docker コンテナで実行
- PDFリンクとカテゴリ情報を含む詳細な投稿

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

- **自動実行**: 12時間おき UTC 0:00 と 12:00 (日本時間 9:00 と 21:00)
- **手動実行**: GitHub Actions の "Run workflow" ボタンから実行可能

## 技術仕様

### ArXiv API使用

- **API エンドポイント**: `http://export.arxiv.org/api/query`
- **検索クエリ**: `cat:cond-mat.mtrl-sci`
- **ソート**: 投稿日時の降順
- **最大取得数**: 300件（設定可能）
- **時間フィルタ**: 過去12時間以内の論文のみ（設定可能）

### 時間フィルタを変更する場合

`fetch_new_entries()` 関数内の時間設定を変更してください：

```python
# 例：6時間前から
time_threshold = now - timedelta(hours=6)

# 例：24時間前から
time_threshold = now - timedelta(hours=24)
```

### 実行時間を変更する場合

`.github/workflows/daily-arxiv.yml` の cron 設定を変更してください：

```yaml
# 毎日 UTC 6:00 と 18:00 (日本時間 15:00 と 3:00) に実行
- cron: '0 6 * * *'
- cron: '0 18 * * *'
```
