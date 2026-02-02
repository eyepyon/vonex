# インストールガイド

## 必要条件

- Python 3.9 以上
- pip（Pythonパッケージマネージャー）
- Vonage アカウントと API 認証情報
- ngrok または公開サーバー（Webhook受信用）

## インストール手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/example/vonage-voice-recorder.git
cd vonage-voice-recorder
```

### 2. 仮想環境の作成（推奨）

```bash
# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
# Windows (cmd)
venv\Scripts\activate

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# macOS / Linux
source venv/bin/activate
```

### 3. 依存関係のインストール

```bash
# 基本的な依存関係
pip install -r requirements.txt

# または pip を使用してパッケージとしてインストール
pip install -e .

# 開発用依存関係も含める場合
pip install -e ".[dev]"

# PostgreSQL サポートが必要な場合
pip install -e ".[postgres]"
```

## Vonage の設定

### 1. Vonage アカウントの作成

1. [Vonage Dashboard](https://dashboard.nexmo.com/) にアクセス
2. アカウントを作成またはログイン
3. API キーと API シークレットを取得

### 2. Vonage アプリケーションの作成

1. Vonage Dashboard で「Applications」→「Create a new application」
2. アプリケーション名を入力
3. 「Voice」機能を有効化
4. Webhook URL を設定（後で更新可能）:
   - Answer URL: `https://your-domain.com/webhooks/answer`
   - Event URL: `https://your-domain.com/webhooks/event`
5. 秘密鍵ファイル（`private.key`）をダウンロードしてプロジェクトルートに保存
6. アプリケーション ID をメモ

### 3. 電話番号の取得

1. Vonage Dashboard で「Numbers」→「Buy numbers」
2. 日本の番号を購入（または既存の番号を使用）
3. 番号を作成したアプリケーションにリンク

## 環境変数の設定

プロジェクトルートに `.env` ファイルを作成：

```bash
# Vonage API 認証情報（必須）
VONAGE_API_KEY=your_api_key
VONAGE_API_SECRET=your_api_secret
VONAGE_APPLICATION_ID=your_application_id
VONAGE_PRIVATE_KEY_PATH=./private.key

# Webhook 設定（必須）
WEBHOOK_BASE_URL=https://your-domain.com

# 音声アナウンス設定（オプション）
GREETING_MESSAGE=お電話ありがとうございます。ただいま電話に出ることができません。発信音の後にメッセージをお残しください。
GREETING_LANGUAGE=ja-JP
GREETING_STYLE=0

# 録音設定（オプション）
MAX_RECORDING_DURATION=60
RECORDING_FORMAT=mp3
END_ON_SILENCE=3

# ロギング設定（オプション）
LOG_LEVEL=INFO
```

### 環境変数一覧

| 変数名 | 必須 | デフォルト値 | 説明 |
|--------|------|-------------|------|
| `VONAGE_API_KEY` | ✅ | - | Vonage API キー |
| `VONAGE_API_SECRET` | ✅ | - | Vonage API シークレット |
| `VONAGE_APPLICATION_ID` | ✅ | - | Vonage アプリケーション ID |
| `VONAGE_PRIVATE_KEY_PATH` | ✅ | - | 秘密鍵ファイルのパス |
| `WEBHOOK_BASE_URL` | ✅ | - | Webhook のベース URL |
| `GREETING_MESSAGE` | ❌ | 日本語グリーティング | 音声アナウンスメッセージ |
| `GREETING_LANGUAGE` | ❌ | `ja-JP` | 音声言語コード |
| `GREETING_STYLE` | ❌ | `0` | 音声スタイル |
| `MAX_RECORDING_DURATION` | ❌ | `60` | 最大録音時間（秒） |
| `RECORDING_FORMAT` | ❌ | `mp3` | 録音フォーマット（mp3/wav/ogg） |
| `END_ON_SILENCE` | ❌ | `3` | 無音終了時間（秒） |
| `LOG_LEVEL` | ❌ | `INFO` | ログレベル |

## ローカル開発環境のセットアップ

### ngrok を使用した Webhook 受信

ローカル開発では ngrok を使用して外部からアクセス可能な URL を取得します。

```bash
# ngrok のインストール（まだの場合）
# https://ngrok.com/download からダウンロード

# ngrok を起動（ポート 5000）
ngrok http 5000
```

ngrok が表示する HTTPS URL（例: `https://abc123.ngrok.io`）を `.env` の `WEBHOOK_BASE_URL` に設定します。

## アプリケーションの起動

```bash
# 開発サーバーの起動
python main.py

# または Flask の開発サーバーを直接使用
flask --app src.app run --host=0.0.0.0 --port=5000
```

サーバーが起動したら、以下のエンドポイントが利用可能になります：

- `GET /webhooks/answer` - 着信電話の応答
- `POST /webhooks/recording` - 録音完了通知
- `POST /webhooks/event` - 通話イベント通知

## 動作確認

1. Vonage Dashboard でアプリケーションの Webhook URL を更新
2. 購入した電話番号に電話をかける
3. 音声アナウンスが再生され、録音が開始されることを確認
4. ログ出力で録音メタデータが保存されていることを確認

## テストの実行

```bash
# 全テストを実行
pytest

# カバレッジレポート付きで実行
pytest --cov=src --cov-report=html

# 特定のテストファイルを実行
pytest tests/test_ncco_builder.py

# 詳細出力で実行
pytest -v
```

## トラブルシューティング

### よくある問題

#### 1. 環境変数が読み込まれない

```bash
# python-dotenv がインストールされているか確認
pip install python-dotenv

# .env ファイルがプロジェクトルートにあるか確認
ls -la .env
```

#### 2. Webhook が受信されない

- ngrok が正しく起動しているか確認
- Vonage Dashboard の Webhook URL が正しいか確認
- ファイアウォールがポート 5000 をブロックしていないか確認

#### 3. 秘密鍵エラー

```bash
# 秘密鍵ファイルのパスが正しいか確認
ls -la private.key

# ファイルの権限を確認（Linux/macOS）
chmod 600 private.key
```

#### 4. 録音が保存されない

- データベースファイル（`voice_recorder.db`）の書き込み権限を確認
- ログ出力でエラーメッセージを確認

## 次のステップ

- [設計書](./design.md) - システムアーキテクチャの詳細
- [要件定義書](./requirements.md) - 機能要件の詳細
- [実装計画](./tasks.md) - 実装タスクの一覧
