#!/usr/bin/env python3
"""
Vonage Voice Recorder アプリケーションエントリーポイント

このモジュールはアプリケーションのメインエントリーポイントです。
設定の読み込み、検証、コンポーネントの初期化を行い、
Flask 開発サーバーを起動します。

Requirements:
    - 5.1: 環境変数から設定を読み込む
    - 5.2: Vonage API 認証情報（API キーとシークレット）を必須とする
    - 5.6: 必須設定が欠落している場合、明確なエラーメッセージで起動に失敗する

Usage:
    python main.py

Environment Variables (Required):
    - VONAGE_API_KEY: Vonage API キー
    - VONAGE_API_SECRET: Vonage API シークレット
    - VONAGE_APPLICATION_ID: Vonage アプリケーション ID
    - VONAGE_PRIVATE_KEY_PATH: Vonage 秘密鍵ファイルパス
    - WEBHOOK_BASE_URL: Webhook のベース URL

Environment Variables (Optional):
    - GREETING_MESSAGE: 音声アナウンスメッセージ
    - GREETING_LANGUAGE: 音声言語 (デフォルト: ja-JP)
    - GREETING_STYLE: 音声スタイル (デフォルト: 0)
    - MAX_RECORDING_DURATION: 最大録音時間（秒） (デフォルト: 60)
    - RECORDING_FORMAT: 録音フォーマット (デフォルト: mp3)
    - END_ON_SILENCE: 無音終了時間（秒） (デフォルト: 3)
    - LOG_LEVEL: ログレベル (デフォルト: INFO)
    - HOST: サーバーホスト (デフォルト: 0.0.0.0)
    - PORT: サーバーポート (デフォルト: 5000)
    - DEBUG: デバッグモード (デフォルト: False)
"""

import os
import sys

from src.config import Config, ConfigurationError
from src.app import create_app


def main() -> int:
    """
    アプリケーションのメインエントリーポイント
    
    設定を読み込み、検証し、Flask アプリケーションを起動します。
    
    Returns:
        int: 終了コード (0: 正常終了, 1: エラー終了)
    
    Requirements:
        - 5.1: 環境変数から設定を読み込む
        - 5.2: Vonage API 認証情報を必須とする
        - 5.6: 必須設定が欠落している場合、明確なエラーメッセージで起動に失敗する
    """
    try:
        # 設定を環境変数から読み込み (Requirements 5.1)
        # Config.from_env() は内部で validate() を呼び出し、
        # 必須設定の検証を行います (Requirements 5.2, 5.6)
        print("設定を読み込んでいます...")
        config = Config.from_env()
        print("設定の読み込みが完了しました。")
        
        # Flask アプリケーションを作成
        print("アプリケーションを初期化しています...")
        app = create_app(config)
        print("アプリケーションの初期化が完了しました。")
        
        # サーバー設定を環境変数から取得
        host = os.environ.get("HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", "5000"))
        debug = os.environ.get("DEBUG", "").lower() in ("true", "1", "yes")
        
        # Flask 開発サーバーを起動
        print(f"サーバーを起動しています... (host={host}, port={port}, debug={debug})")
        print(f"Webhook URL: {config.webhook_base_url}")
        print("サーバーを停止するには Ctrl+C を押してください。")
        
        app.run(host=host, port=port, debug=debug)
        
        return 0
        
    except ConfigurationError as e:
        # 設定エラーの場合、明確なエラーメッセージを表示 (Requirements 5.6)
        print(f"\n[エラー] 設定エラーが発生しました:", file=sys.stderr)
        print(f"  {e}", file=sys.stderr)
        print("\n必要な環境変数を設定してから再度実行してください。", file=sys.stderr)
        print("\n必須の環境変数:", file=sys.stderr)
        print("  - VONAGE_API_KEY: Vonage API キー", file=sys.stderr)
        print("  - VONAGE_API_SECRET: Vonage API シークレット", file=sys.stderr)
        print("  - VONAGE_APPLICATION_ID: Vonage アプリケーション ID", file=sys.stderr)
        print("  - VONAGE_PRIVATE_KEY_PATH: Vonage 秘密鍵ファイルパス", file=sys.stderr)
        print("  - WEBHOOK_BASE_URL: Webhook のベース URL", file=sys.stderr)
        return 1
        
    except KeyboardInterrupt:
        # Ctrl+C による終了
        print("\nサーバーを停止しました。")
        return 0
        
    except Exception as e:
        # 予期しないエラー
        print(f"\n[エラー] 予期しないエラーが発生しました:", file=sys.stderr)
        print(f"  {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
