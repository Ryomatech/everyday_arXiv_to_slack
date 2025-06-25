FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# スクリプトをコピー
COPY arxiv_to_slack.py .
COPY ml_keywords.py .

# スクリプトを実行可能にする
RUN chmod +x arxiv_to_slack.py

# デフォルト実行コマンド
CMD ["python", "arxiv_to_slack.py"]
