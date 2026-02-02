# 実装計画 (Implementation Plan): Vonage Voice Recorder

## 概要 (Overview)

本実装計画は、Vonage Voice APIを使用した音声録音システムの段階的な実装手順を定義します。各タスクは前のタスクの成果物を基に構築され、最終的に完全に動作するシステムを実現します。

## タスク (Tasks)

- [~] 1. プロジェクト構造とコア設定のセットアップ
  - [-] 1.1 プロジェクトディレクトリ構造を作成
    - `src/` ディレクトリにメインコードを配置
    - `tests/` ディレクトリにテストコードを配置
    - `requirements.txt` と `pyproject.toml` を作成
    - _Requirements: 5.1_
  
  - [x] 1.2 Config クラスを実装
    - 環境変数から設定を読み込む `Config.from_env()` メソッドを実装
    - 必須設定のバリデーション `validate()` メソッドを実装
    - デフォルト値の設定（日本語グリーティング等）
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_
  
  - [ ]* 1.3 Config クラスのユニットテストを作成
    - 正常系: 有効な環境変数からの読み込み
    - エラー系: 必須設定欠落時のエラー
    - _Requirements: 5.6_

- [x] 2. データモデルとストレージレイヤーの実装
  - [x] 2.1 データモデルクラスを実装
    - `Recording` dataclass を作成
    - `CallLog` dataclass を作成
    - _Requirements: 4.2_
  
  - [x] 2.2 Storage 抽象基底クラスを実装
    - `save_recording`, `get_recording`, `list_recordings` メソッドを定義
    - `save_call_log` メソッドを定義
    - _Requirements: 4.1, 4.4, 4.5_
  
  - [x] 2.3 SQLiteStorage 実装を作成
    - SQLite データベース接続とテーブル作成
    - CRUD 操作の実装
    - _Requirements: 4.1, 4.4, 4.5_
  
  - [ ]* 2.4 プロパティテスト: Recording Metadata Persistence Round-Trip
    - **Property 5: Recording Metadata Persistence Round-Trip**
    - **Validates: Requirements 3.3, 3.4, 4.1, 4.2, 4.4**
  
  - [ ]* 2.5 プロパティテスト: Recording List Filtering
    - **Property 6: Recording List Filtering**
    - **Validates: Requirements 4.5**

- [x] 3. チェックポイント - ストレージレイヤーの検証
  - すべてのテストが通過することを確認し、質問があればユーザーに確認

- [x] 4. NCCO Builder の実装
  - [x] 4.1 NCCO アクション dataclass を実装
    - `TalkAction` dataclass を作成
    - `RecordAction` dataclass を作成
    - _Requirements: 2.1, 2.2, 3.1, 3.2_
  
  - [x] 4.2 NCCOBuilder クラスを実装
    - `build_voicemail_ncco()` メソッドを実装
    - Talk アクションと Record アクションの構築
    - 設定値の適用（メッセージ、言語、タイムアウト等）
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.5_
  
  - [ ]* 4.3 プロパティテスト: NCCO Structure Validity
    - **Property 1: NCCO Structure Validity**
    - **Validates: Requirements 1.1, 2.1, 2.2, 3.1, 3.2**
  
  - [ ]* 4.4 プロパティテスト: Configuration Application
    - **Property 2: Configuration Application**
    - **Validates: Requirements 2.3, 2.4, 3.5, 5.1, 5.3, 5.4, 5.5**

- [x] 5. Recording Manager の実装
  - [x] 5.1 RecordingManager クラスを実装
    - `save_recording()` メソッドを実装
    - `get_recording()` メソッドを実装
    - `list_recordings()` メソッドを実装
    - _Requirements: 3.4, 4.1, 4.4, 4.5_
  
  - [ ]* 5.2 RecordingManager のユニットテストを作成
    - 正常系: 録音メタデータの保存と取得
    - エッジケース: 存在しないUUIDでの検索
    - _Requirements: 4.4_

- [x] 6. チェックポイント - コアコンポーネントの検証
  - すべてのテストが通過することを確認し、質問があればユーザーに確認

- [x] 7. Webhook Handler の実装
  - [x] 7.1 Flask アプリケーションの基本構造を作成
    - Flask アプリケーションインスタンスの作成
    - 構造化ロギングの設定（structlog）
    - _Requirements: 6.1, 6.5_
  
  - [x] 7.2 Answer Webhook エンドポイントを実装
    - `GET /webhooks/answer` ルートを作成
    - 通話パラメータの抽出
    - NCCO の生成と返却
    - 通話ログの保存
    - _Requirements: 1.1, 1.2, 1.5, 2.1_
  
  - [x] 7.3 Recording Webhook エンドポイントを実装
    - `POST /webhooks/recording` ルートを作成
    - 録音メタデータの抽出と保存
    - _Requirements: 3.3, 3.4, 4.1_
  
  - [x] 7.4 Event Webhook エンドポイントを実装
    - `POST /webhooks/event` ルートを作成
    - 通話ステータスの更新
    - _Requirements: 3.6, 3.7_
  
  - [x] 7.5 エラーハンドリングを実装
    - 不正なリクエストの検出と拒否
    - エラーログの出力
    - _Requirements: 1.4, 6.2, 6.4_
  
  - [ ]* 7.6 プロパティテスト: Webhook Data Extraction
    - **Property 3: Webhook Data Extraction**
    - **Validates: Requirements 1.2**
  
  - [ ]* 7.7 プロパティテスト: Error Response Handling
    - **Property 4: Error Response Handling**
    - **Validates: Requirements 1.4**

- [x] 8. ロギングシステムの実装
  - [x] 8.1 構造化ロギングを設定
    - structlog の設定
    - JSON フォーマットの出力
    - ログレベルの設定
    - _Requirements: 6.1, 6.3, 6.5_
  
  - [ ]* 8.2 プロパティテスト: Structured Logging Format
    - **Property 7: Structured Logging Format**
    - **Validates: Requirements 1.5, 6.1, 6.2, 6.3, 6.5**

- [x] 9. 統合とエントリーポイント
  - [x] 9.1 アプリケーションエントリーポイントを作成
    - `main.py` を作成
    - 設定の読み込みと検証
    - コンポーネントの初期化と接続
    - _Requirements: 5.1, 5.2, 5.6_
  
  - [ ]* 9.2 統合テストを作成
    - 完全な通話フローのテスト
    - Webhook シーケンスのテスト
    - _Requirements: 1.1, 2.1, 3.1, 3.3_

- [x] 10. 最終チェックポイント - 全テストの検証
  - すべてのテストが通過することを確認し、質問があればユーザーに確認

## 備考 (Notes)

- `*` マークのタスクはオプションであり、MVPを優先する場合はスキップ可能
- 各タスクは特定の要件への追跡可能性を持つ
- チェックポイントで段階的な検証を実施
- プロパティテストは普遍的な正確性プロパティを検証
- ユニットテストは特定の例とエッジケースを検証
