"""
Flask アプリケーションモジュール (Flask Application Module)

Vonage Voice Recorder の Flask アプリケーションを提供します。
Webhook エンドポイントと構造化ロギングを設定します。

Requirements:
    - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
    - 6.1: 適切なログレベルで操作をログ出力
    - 6.2: エラー発生時にスタックトレースとコンテキスト情報をログ出力
    - 6.4: Vonage API エラーを適切に処理し、詳細をログ出力
    - 6.5: 構造化ロギングフォーマットを使用
"""

import logging
import sys
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import structlog
from flask import Flask, jsonify, request, Response

from .config import Config
from .models import CallLog
from .ncco_builder import NCCOBuilder
from .recording_manager import RecordingManager
from .storage import SQLiteStorage, Storage


class WebhookValidationError(Exception):
    """
    Webhook 検証エラー
    
    不正な Webhook リクエストを検出した場合に発生します。
    
    Attributes:
        message: エラーメッセージ
        error_type: エラーの種類
    """
    
    def __init__(self, message: str, error_type: str = "validation_error"):
        super().__init__(message)
        self.message = message
        self.error_type = error_type


class VonageAPIError(Exception):
    """
    Vonage API エラー
    
    Vonage API との通信でエラーが発生した場合に発生します。
    
    Attributes:
        message: エラーメッセージ
        status_code: HTTP ステータスコード
        details: 追加の詳細情報
    """
    
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


def configure_structlog(log_level: str = "INFO") -> None:
    """
    structlog を設定
    
    JSON フォーマットの構造化ロギングを設定します。
    すべてのログ出力は timestamp, level, message フィールドを含みます。
    
    Args:
        log_level: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Requirements:
        - 6.1: 適切なログレベルで操作をログ出力
        - 6.5: 構造化ロギングフォーマットを使用
    """
    # 標準ライブラリの logging を設定
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )
    
    # structlog のプロセッサチェーンを設定
    structlog.configure(
        processors=[
            # コンテキスト情報を追加
            structlog.contextvars.merge_contextvars,
            # ログレベルを追加
            structlog.stdlib.add_log_level,
            # ロガー名を追加
            structlog.stdlib.add_logger_name,
            # タイムスタンプを追加
            structlog.processors.TimeStamper(fmt="iso"),
            # スタックトレース情報を追加
            structlog.processors.StackInfoRenderer(),
            # 例外情報をフォーマット
            structlog.processors.format_exc_info,
            # Unicode をデコード
            structlog.processors.UnicodeDecoder(),
            # JSON フォーマットでレンダリング
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """
    構造化ロガーを取得
    
    Args:
        name: ロガー名
    
    Returns:
        構造化ロガーインスタンス
    """
    return structlog.get_logger(name)


def validate_json_request(data: Any, required_fields: Optional[list] = None) -> Tuple[bool, Optional[str]]:
    """
    JSON リクエストを検証
    
    Args:
        data: 検証するデータ
        required_fields: 必須フィールドのリスト（オプション）
    
    Returns:
        (検証結果, エラーメッセージ) のタプル
    
    Requirements:
        - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
    """
    if data is None:
        return False, "Invalid JSON: request body is empty or malformed"
    
    if not isinstance(data, dict):
        return False, "Invalid JSON: request body must be a JSON object"
    
    if required_fields:
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, None


def create_error_response(
    error_type: str,
    message: str,
    status_code: int,
    details: Optional[Dict[str, Any]] = None
) -> Tuple[Response, int]:
    """
    エラーレスポンスを作成
    
    Args:
        error_type: エラーの種類
        message: エラーメッセージ
        status_code: HTTP ステータスコード
        details: 追加の詳細情報（オプション）
    
    Returns:
        (JSON レスポンス, ステータスコード) のタプル
    
    Requirements:
        - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
    """
    response_body = {
        "error": error_type,
        "message": message,
        "status_code": status_code
    }
    if details:
        response_body["details"] = details
    
    return jsonify(response_body), status_code


class WebhookHandler:
    """
    Vonage Webhook を処理するハンドラー
    
    着信電話、録音完了、通話イベントの Webhook を処理します。
    
    Attributes:
        ncco_builder: NCCO を構築するビルダー
        recording_manager: 録音データを管理するマネージャー
        logger: 構造化ロガー
        music_generator: 音楽生成器（オプション）
    
    Requirements:
        - 1.1: 着信電話を受け付け、有効な NCCO で応答
        - 1.2: 発信者番号と通話 UUID を抽出
        - 3.3: 録音完了 Webhook を受信し、Recording_URL を取得
        - 6.1: 適切なログレベルで操作をログ出力
    """
    
    def __init__(
        self,
        ncco_builder: NCCOBuilder,
        recording_manager: RecordingManager,
        storage: Storage,
        music_generator: Optional[Any] = None,
        music_style: str = "j-pop, emotional, heartfelt, japanese"
    ):
        """
        WebhookHandler を初期化
        
        Args:
            ncco_builder: NCCO を構築するビルダー
            recording_manager: 録音データを管理するマネージャー
            storage: ストレージレイヤー
            music_generator: 音楽生成器（オプション）
            music_style: 音楽スタイル
        """
        self.ncco_builder = ncco_builder
        self.recording_manager = recording_manager
        self.storage = storage
        self.music_generator = music_generator
        self.music_style = music_style
        self.logger = get_logger(__name__)
    
    def handle_answer(self, params: Dict[str, Any]) -> list:
        """
        着信電話の Answer Webhook を処理
        
        Vonage から送信される着信電話の Webhook を処理し、
        NCCO を生成して返却します。
        
        Args:
            params: Vonage から送信されるパラメータ
                - uuid: 通話 UUID
                - from: 発信者番号
                - to: 着信番号
                - conversation_uuid: 会話 UUID
        
        Returns:
            NCCO アクションのリスト
        
        Requirements:
            - 1.1: 着信電話を受け付け、有効な NCCO で応答
            - 1.2: 発信者番号と通話 UUID を抽出
            - 1.5: 通話詳細をログ出力
            - 2.1: 着信時に音声アナウンスを再生
        """
        # 通話パラメータを抽出 (Requirements 1.2)
        call_uuid = params.get("uuid", "")
        caller_number = params.get("from", "")
        called_number = params.get("to", "")
        conversation_uuid = params.get("conversation_uuid", "")
        
        # 通話詳細をログ出力 (Requirements 1.5)
        current_time = datetime.utcnow()
        self.logger.info(
            "incoming_call_received",
            call_uuid=call_uuid,
            caller_number=caller_number,
            called_number=called_number,
            conversation_uuid=conversation_uuid,
            timestamp=current_time.isoformat()
        )
        
        # 通話ログを保存 (Requirements 1.5)
        call_log = CallLog(
            id=str(uuid.uuid4()),
            call_uuid=call_uuid,
            caller_number=caller_number,
            called_number=called_number,
            status="answered",
            direction="inbound",
            started_at=current_time,
            ended_at=None,
            created_at=current_time
        )
        self.storage.save_call_log(call_log)
        
        self.logger.debug(
            "call_log_saved",
            call_uuid=call_uuid,
            call_log_id=call_log.id
        )
        
        # NCCO を生成 (Requirements 1.1, 2.1)
        ncco = self.ncco_builder.build_voicemail_ncco(call_uuid)
        
        self.logger.info(
            "ncco_generated",
            call_uuid=call_uuid,
            ncco_actions=len(ncco)
        )
        
        return ncco
    
    def handle_recording(self, data: Dict[str, Any]) -> None:
        """
        録音完了 Webhook を処理
        
        Vonage から送信される録音完了の Webhook を処理し、
        録音メタデータを保存します。
        
        Args:
            data: 録音データ
                - recording_url: 録音ファイル URL
                - recording_uuid: 録音 UUID
                - conversation_uuid: 会話 UUID
                - start_time: 録音開始時刻
                - end_time: 録音終了時刻
                - size: ファイルサイズ
                - duration: 録音時間（秒）
        
        Requirements:
            - 3.3: 録音完了 Webhook を受信し、Recording_URL を取得
            - 3.4: 録音メタデータを保存
            - 4.1: 録音完了時にメタデータをストレージに永続化
        """
        from .recording_manager import RecordingMetadata
        
        # 録音データを抽出 (Requirements 3.3)
        recording_url = data.get("recording_url", "")
        recording_uuid_value = data.get("recording_uuid", "")
        conversation_uuid = data.get("conversation_uuid", "")
        start_time = data.get("start_time", "")
        end_time = data.get("end_time", "")
        file_size = data.get("size", 0)
        duration = data.get("duration", 0)
        
        # 通話 UUID を取得（conversation_uuid を使用）
        call_uuid = conversation_uuid
        
        # 録音詳細をログ出力
        self.logger.info(
            "recording_webhook_received",
            recording_url=recording_url,
            recording_uuid=recording_uuid_value,
            conversation_uuid=conversation_uuid,
            duration=duration,
            file_size=file_size,
            start_time=start_time,
            end_time=end_time
        )
        
        # タイムスタンプを解析
        try:
            if start_time:
                timestamp = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            else:
                timestamp = datetime.utcnow()
        except (ValueError, AttributeError):
            timestamp = datetime.utcnow()
        
        # RecordingMetadata を作成
        metadata = RecordingMetadata(
            id=str(uuid.uuid4()),
            call_uuid=call_uuid,
            caller_number="",  # Webhook には発信者番号が含まれない場合がある
            recording_url=recording_url,
            duration=int(duration) if duration else 0,
            timestamp=timestamp,
            status="completed"
        )
        
        # 録音メタデータを保存 (Requirements 3.4, 4.1)
        self.recording_manager.save_recording(
            metadata=metadata,
            conversation_uuid=conversation_uuid,
            recording_uuid=recording_uuid_value,
            file_size=int(file_size) if file_size else 0
        )
        
        self.logger.info(
            "recording_metadata_saved",
            recording_id=metadata.id,
            call_uuid=call_uuid,
            recording_url=recording_url,
            duration=duration
        )
        
        # 音楽生成が有効な場合、バックグラウンドで処理を開始
        if self.music_generator:
            # 通話ログから発信者番号を取得
            call_log = self.storage.get_call_log(call_uuid)
            caller_number = call_log.caller_number if call_log else ""
            
            # ローカルファイルパスを取得
            local_file_path = self.recording_manager.recordings_dir + "/" + metadata.id + ".mp3"
            
            if caller_number and local_file_path:
                self.logger.info(
                    "starting_music_generation",
                    recording_id=metadata.id,
                    caller_number=caller_number,
                    local_file_path=local_file_path
                )
                
                # 別スレッドで音楽生成を実行（Webhookレスポンスをブロックしないため）
                import threading
                thread = threading.Thread(
                    target=self._process_music_generation,
                    args=(local_file_path, caller_number, metadata.id)
                )
                thread.daemon = True
                thread.start()
    
    def _process_music_generation(
        self,
        audio_file_path: str,
        caller_number: str,
        recording_id: str
    ) -> None:
        """
        バックグラウンドで音楽生成を処理
        
        Args:
            audio_file_path: 音声ファイルのパス
            caller_number: 発信者の電話番号
            recording_id: 録音ID
        """
        try:
            self.logger.info(
                "music_generation_started",
                recording_id=recording_id,
                audio_file_path=audio_file_path
            )
            
            music_url = self.music_generator.process_voicemail(
                audio_file_path=audio_file_path,
                caller_number=caller_number,
                music_style=self.music_style
            )
            
            if music_url:
                self.logger.info(
                    "music_generation_completed",
                    recording_id=recording_id,
                    music_url=music_url
                )
            else:
                self.logger.warning(
                    "music_generation_failed",
                    recording_id=recording_id
                )
                
        except Exception as e:
            self.logger.error(
                "music_generation_error",
                recording_id=recording_id,
                error=str(e),
                exc_info=True
            )
    
    def handle_event(self, data: Dict[str, Any]) -> None:
        """
        通話イベント Webhook を処理
        
        Vonage から送信される通話イベントの Webhook を処理し、
        通話ステータスを更新します。
        
        Args:
            data: イベントデータ
                - uuid: 通話 UUID
                - status: 通話ステータス
                - timestamp: イベント発生時刻
        
        Requirements:
            - 3.6: 発信者が録音中に切断した場合、部分録音を保存
            - 3.7: 録音が失敗した場合、関連する通話詳細とともにエラーをログ出力
        """
        # イベントデータを抽出
        call_uuid = data.get("uuid", "")
        status = data.get("status", "")
        timestamp_str = data.get("timestamp", "")
        
        # イベント詳細をログ出力
        self.logger.info(
            "event_webhook_received",
            call_uuid=call_uuid,
            status=status,
            timestamp=timestamp_str
        )
        
        # タイムスタンプを解析
        try:
            if timestamp_str:
                event_timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                event_timestamp = datetime.utcnow()
        except (ValueError, AttributeError):
            event_timestamp = datetime.utcnow()
        
        # 通話終了ステータスの場合、ended_at を設定
        terminal_statuses = ["completed", "failed", "rejected", "busy", "cancelled", "timeout", "unanswered"]
        ended_at = event_timestamp if status in terminal_statuses else None
        
        # 通話ログのステータスを更新
        if call_uuid:
            updated = self.storage.update_call_log_status(
                call_uuid=call_uuid,
                status=status,
                ended_at=ended_at
            )
            
            if updated:
                self.logger.info(
                    "call_log_status_updated",
                    call_uuid=call_uuid,
                    new_status=status,
                    ended_at=ended_at.isoformat() if ended_at else None
                )
            else:
                self.logger.warning(
                    "call_log_not_found_for_update",
                    call_uuid=call_uuid,
                    status=status
                )
        
        # 録音失敗の場合、エラーをログ出力 (Requirements 3.7)
        if status == "failed":
            reason = data.get("reason", "unknown")
            self.logger.error(
                "recording_failed",
                call_uuid=call_uuid,
                status=status,
                reason=reason,
                timestamp=timestamp_str,
                event_data=data
            )


def create_app(config: Optional[Config] = None) -> Flask:
    """
    Flask アプリケーションを作成
    
    Flask アプリケーションインスタンスを作成し、
    構造化ロギングとヘルスチェックエンドポイントを設定します。
    
    Args:
        config: アプリケーション設定（None の場合は環境変数から読み込み）
    
    Returns:
        設定済みの Flask アプリケーション
    
    Requirements:
        - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
        - 6.1: 適切なログレベルで操作をログ出力
        - 6.2: エラー発生時にスタックトレースとコンテキスト情報をログ出力
        - 6.4: Vonage API エラーを適切に処理し、詳細をログ出力
        - 6.5: 構造化ロギングフォーマットを使用
    """
    # Flask アプリケーションインスタンスを作成
    app = Flask(__name__)
    
    # 設定を読み込み（テスト時は外部から注入可能）
    if config is None:
        config = Config.from_env()
    
    # アプリケーション設定を保存
    app.config["VOICE_RECORDER_CONFIG"] = config
    
    # 構造化ロギングを設定
    configure_structlog(config.log_level)
    
    # ロガーを取得
    logger = get_logger(__name__)
    logger.info(
        "application_initialized",
        log_level=config.log_level,
        webhook_base_url=config.webhook_base_url
    )
    
    # ストレージレイヤーを初期化
    storage = SQLiteStorage()
    app.config["STORAGE"] = storage
    
    # NCCO Builder を初期化
    ncco_builder = NCCOBuilder(config)
    app.config["NCCO_BUILDER"] = ncco_builder
    
    # Recording Manager を初期化（Vonage認証情報を渡して音声ファイルダウンロードを有効化）
    recording_manager = RecordingManager(
        storage=storage,
        vonage_api_key=config.vonage_api_key,
        vonage_api_secret=config.vonage_api_secret
    )
    app.config["RECORDING_MANAGER"] = recording_manager
    
    # Music Generator を初期化（有効な場合のみ）
    music_generator = None
    if config.enable_music_generation:
        if config.openai_api_key and config.mureka_api_key and config.vonage_sms_from:
            from .music_generator import MusicGenerator
            music_generator = MusicGenerator(
                openai_api_key=config.openai_api_key,
                mureka_api_key=config.mureka_api_key,
                vonage_api_key=config.vonage_api_key,
                vonage_api_secret=config.vonage_api_secret,
                vonage_from_number=config.vonage_sms_from
            )
            logger.info(
                "music_generator_initialized",
                music_style=config.music_style
            )
        else:
            logger.warning(
                "music_generator_disabled",
                reason="Missing required API keys (OPENAI_API_KEY, MUREKA_API_KEY, VONAGE_SMS_FROM)"
            )
    
    # Webhook Handler を初期化
    webhook_handler = WebhookHandler(
        ncco_builder=ncco_builder,
        recording_manager=recording_manager,
        storage=storage,
        music_generator=music_generator,
        music_style=config.music_style
    )
    app.config["WEBHOOK_HANDLER"] = webhook_handler
    
    # ==========================================================================
    # エラーハンドラー (Error Handlers)
    # Requirements: 1.4, 6.2, 6.4
    # ==========================================================================
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        """
        400 Bad Request エラーハンドラー
        
        不正なリクエスト（無効な JSON、必須フィールド欠落など）を処理します。
        
        Requirements:
            - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
            - 6.2: エラー発生時にスタックトレースとコンテキスト情報をログ出力
        """
        logger.error(
            "bad_request_error",
            error_type="bad_request",
            error_message=str(error),
            path=request.path,
            method=request.method,
            content_type=request.content_type,
            exc_info=True
        )
        return create_error_response(
            error_type="bad_request",
            message=str(error.description) if hasattr(error, 'description') else "Bad Request",
            status_code=400
        )
    
    @app.errorhandler(401)
    def handle_unauthorized(error):
        """
        401 Unauthorized エラーハンドラー
        
        認証失敗（署名検証失敗など）を処理します。
        
        Requirements:
            - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
            - 6.2: エラー発生時にスタックトレースとコンテキスト情報をログ出力
        """
        logger.error(
            "unauthorized_error",
            error_type="unauthorized",
            error_message=str(error),
            path=request.path,
            method=request.method,
            exc_info=True
        )
        return create_error_response(
            error_type="unauthorized",
            message=str(error.description) if hasattr(error, 'description') else "Unauthorized",
            status_code=401
        )
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """
        405 Method Not Allowed エラーハンドラー
        
        許可されていない HTTP メソッドを処理します。
        
        Requirements:
            - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
        """
        logger.warning(
            "method_not_allowed_error",
            error_type="method_not_allowed",
            error_message=str(error),
            path=request.path,
            method=request.method
        )
        return create_error_response(
            error_type="method_not_allowed",
            message=str(error.description) if hasattr(error, 'description') else "Method Not Allowed",
            status_code=405
        )
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """
        500 Internal Server Error エラーハンドラー
        
        内部エラーを処理し、スタックトレースをログ出力します。
        
        Requirements:
            - 6.2: エラー発生時にスタックトレースとコンテキスト情報をログ出力
        """
        # スタックトレースを取得
        stack_trace = traceback.format_exc()
        
        logger.error(
            "internal_server_error",
            error_type="internal_error",
            error_message=str(error),
            path=request.path,
            method=request.method,
            stack_trace=stack_trace,
            exc_info=True
        )
        return create_error_response(
            error_type="internal_error",
            message="Internal Server Error",
            status_code=500
        )
    
    @app.errorhandler(WebhookValidationError)
    def handle_webhook_validation_error(error):
        """
        WebhookValidationError エラーハンドラー
        
        Webhook 検証エラーを処理します。
        
        Requirements:
            - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
            - 6.2: エラー発生時にスタックトレースとコンテキスト情報をログ出力
        """
        logger.error(
            "webhook_validation_error",
            error_type=error.error_type,
            error_message=error.message,
            path=request.path,
            method=request.method,
            content_type=request.content_type,
            exc_info=True
        )
        return create_error_response(
            error_type=error.error_type,
            message=error.message,
            status_code=400
        )
    
    @app.errorhandler(VonageAPIError)
    def handle_vonage_api_error(error):
        """
        VonageAPIError エラーハンドラー
        
        Vonage API エラーを処理します。
        
        Requirements:
            - 6.4: Vonage API エラーを適切に処理し、詳細をログ出力
        """
        logger.error(
            "vonage_api_error",
            error_type="vonage_api_error",
            error_message=error.message,
            status_code=error.status_code,
            details=error.details,
            path=request.path,
            method=request.method,
            exc_info=True
        )
        return create_error_response(
            error_type="vonage_api_error",
            message=error.message,
            status_code=error.status_code,
            details=error.details
        )
    
    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        """
        汎用例外ハンドラー
        
        予期しない例外を処理し、スタックトレースをログ出力します。
        
        Requirements:
            - 6.2: エラー発生時にスタックトレースとコンテキスト情報をログ出力
        """
        # スタックトレースを取得
        stack_trace = traceback.format_exc()
        
        logger.error(
            "unhandled_exception",
            error_type=type(error).__name__,
            error_message=str(error),
            path=request.path,
            method=request.method,
            stack_trace=stack_trace,
            exc_info=True
        )
        return create_error_response(
            error_type="internal_error",
            message="An unexpected error occurred",
            status_code=500
        )
    
    # ==========================================================================
    # エンドポイント (Endpoints)
    # ==========================================================================
    
    # ヘルスチェックエンドポイント
    @app.route("/health", methods=["GET"])
    def health_check():
        """
        ヘルスチェックエンドポイント
        
        アプリケーションの稼働状態を確認するためのエンドポイントです。
        
        Returns:
            JSON レスポンス: {"status": "healthy"}
        """
        logger.debug("health_check_requested")
        return jsonify({"status": "healthy"}), 200
    
    # Answer Webhook エンドポイント (Requirements 1.1, 1.2, 1.4, 1.5, 2.1)
    @app.route("/webhooks/answer", methods=["GET"])
    def answer_webhook():
        """
        Answer Webhook エンドポイント
        
        Vonage から着信電話の通知を受け取り、NCCO を返却します。
        
        Query Parameters:
            - uuid: 通話 UUID
            - from: 発信者番号
            - to: 着信番号
            - conversation_uuid: 会話 UUID
        
        Returns:
            JSON レスポンス: NCCO アクションのリスト
        
        Requirements:
            - 1.1: 着信電話を受け付け、有効な NCCO で応答
            - 1.2: 発信者番号と通話 UUID を抽出
            - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
            - 1.5: 通話詳細をログ出力
            - 2.1: 着信時に音声アナウンスを再生
        """
        try:
            logger.debug(
                "answer_webhook_received",
                args=dict(request.args)
            )
            
            # クエリパラメータを抽出
            params = {
                "uuid": request.args.get("uuid", ""),
                "from": request.args.get("from", ""),
                "to": request.args.get("to", ""),
                "conversation_uuid": request.args.get("conversation_uuid", "")
            }
            
            # WebhookHandler で処理
            ncco = webhook_handler.handle_answer(params)
            
            logger.info(
                "answer_webhook_response",
                call_uuid=params["uuid"],
                ncco_actions=len(ncco)
            )
            
            return jsonify(ncco), 200
            
        except WebhookValidationError:
            # WebhookValidationError は専用ハンドラーで処理
            raise
        except VonageAPIError:
            # VonageAPIError は専用ハンドラーで処理
            raise
        except Exception as e:
            # 予期しないエラーをログ出力 (Requirements 6.2)
            logger.error(
                "answer_webhook_error",
                error_type=type(e).__name__,
                error_message=str(e),
                params=dict(request.args),
                stack_trace=traceback.format_exc(),
                exc_info=True
            )
            raise
    
    # Recording Webhook エンドポイント (Requirements 1.4, 3.3, 3.4, 4.1, 6.2)
    @app.route("/webhooks/recording", methods=["POST"])
    def recording_webhook():
        """
        Recording Webhook エンドポイント
        
        Vonage から録音完了の通知を受け取り、メタデータを保存します。
        
        Request Body (JSON):
            - recording_url: 録音ファイル URL
            - recording_uuid: 録音 UUID
            - conversation_uuid: 会話 UUID
            - start_time: 録音開始時刻
            - end_time: 録音終了時刻
            - size: ファイルサイズ
            - duration: 録音時間（秒）
        
        Returns:
            JSON レスポンス: {"status": "ok"}
        
        Requirements:
            - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
            - 3.3: 録音完了 Webhook を受信し、Recording_URL を取得
            - 3.4: 録音メタデータを保存
            - 4.1: 録音完了時にメタデータをストレージに永続化
            - 6.2: エラー発生時にスタックトレースとコンテキスト情報をログ出力
        """
        try:
            logger.debug(
                "recording_webhook_received",
                content_type=request.content_type
            )
            
            # JSON データを取得し検証 (Requirements 1.4)
            try:
                data = request.get_json(force=True, silent=False)
            except Exception as json_error:
                logger.error(
                    "invalid_json_error",
                    error_type="invalid_json",
                    error_message=str(json_error),
                    path=request.path,
                    content_type=request.content_type,
                    exc_info=True
                )
                raise WebhookValidationError(
                    message="Invalid JSON: request body is malformed",
                    error_type="invalid_json"
                )
            
            # データが None の場合は空の辞書として扱う
            if data is None:
                data = {}
            
            # JSON オブジェクトであることを検証
            is_valid, error_message = validate_json_request(data)
            if not is_valid:
                raise WebhookValidationError(
                    message=error_message,
                    error_type="invalid_json"
                )
            
            logger.debug(
                "recording_webhook_data",
                data=data
            )
            
            # WebhookHandler で処理
            webhook_handler.handle_recording(data)
            
            logger.info(
                "recording_webhook_processed",
                recording_url=data.get("recording_url", ""),
                conversation_uuid=data.get("conversation_uuid", "")
            )
            
            return jsonify({"status": "ok"}), 200
            
        except WebhookValidationError:
            # WebhookValidationError は専用ハンドラーで処理
            raise
        except VonageAPIError:
            # VonageAPIError は専用ハンドラーで処理
            raise
        except Exception as e:
            # 予期しないエラーをログ出力 (Requirements 6.2)
            logger.error(
                "recording_webhook_error",
                error_type=type(e).__name__,
                error_message=str(e),
                stack_trace=traceback.format_exc(),
                exc_info=True
            )
            raise
    
    # Event Webhook エンドポイント (Requirements 1.4, 3.6, 3.7, 6.2)
    @app.route("/webhooks/event", methods=["GET", "POST"])
    def event_webhook():
        """
        Event Webhook エンドポイント
        
        Vonage から通話イベントの通知を受け取り、通話ステータスを更新します。
        
        Request Body (JSON):
            - uuid: 通話 UUID
            - status: 通話ステータス
            - timestamp: イベント発生時刻
        
        Returns:
            JSON レスポンス: {"status": "ok"}
        
        Requirements:
            - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
            - 3.6: 発信者が録音中に切断した場合、部分録音を保存
            - 3.7: 録音が失敗した場合、関連する通話詳細とともにエラーをログ出力
            - 6.2: エラー発生時にスタックトレースとコンテキスト情報をログ出力
        """
        try:
            logger.debug(
                "event_webhook_received",
                content_type=request.content_type,
                method=request.method
            )
            
            # GET リクエストの場合はクエリパラメータから、POST の場合は JSON から取得
            if request.method == "GET":
                data = dict(request.args)
            else:
                # JSON データを取得し検証 (Requirements 1.4)
                try:
                    data = request.get_json(force=True, silent=False)
                except Exception as json_error:
                    logger.error(
                        "invalid_json_error",
                        error_type="invalid_json",
                        error_message=str(json_error),
                        path=request.path,
                        content_type=request.content_type,
                        exc_info=True
                    )
                    raise WebhookValidationError(
                        message="Invalid JSON: request body is malformed",
                        error_type="invalid_json"
                    )
                
                # データが None の場合は空の辞書として扱う
                if data is None:
                    data = {}
                
                # JSON オブジェクトであることを検証
                is_valid, error_message = validate_json_request(data)
                if not is_valid:
                    raise WebhookValidationError(
                        message=error_message,
                        error_type="invalid_json"
                    )
            
            logger.debug(
                "event_webhook_data",
                data=data
            )
            
            # WebhookHandler で処理
            webhook_handler.handle_event(data)
            
            logger.info(
                "event_webhook_processed",
                call_uuid=data.get("uuid", ""),
                status=data.get("status", "")
            )
            
            return jsonify({"status": "ok"}), 200
            
        except WebhookValidationError:
            # WebhookValidationError は専用ハンドラーで処理
            raise
        except VonageAPIError:
            # VonageAPIError は専用ハンドラーで処理
            raise
        except Exception as e:
            # 予期しないエラーをログ出力 (Requirements 6.2)
            logger.error(
                "event_webhook_error",
                error_type=type(e).__name__,
                error_message=str(e),
                stack_trace=traceback.format_exc(),
                exc_info=True
            )
            raise
    
    logger.info("application_ready", endpoints=["/health", "/webhooks/answer", "/webhooks/recording", "/webhooks/event"])
    
    return app
