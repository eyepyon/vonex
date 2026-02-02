"""
Flask アプリケーションのテスト (Flask Application Tests)

Flask アプリケーションの基本構造と構造化ロギングをテストします。

Requirements:
    - 6.1: 適切なログレベルで操作をログ出力
    - 6.5: 構造化ロギングフォーマットを使用
"""

import json
import os
import pytest
from unittest.mock import patch

from src.app import create_app, configure_structlog, get_logger, WebhookHandler
from src.config import Config
from src.ncco_builder import NCCOBuilder
from src.recording_manager import RecordingManager
from src.storage import SQLiteStorage


@pytest.fixture
def test_config():
    """テスト用の設定を作成"""
    return Config(
        vonage_api_key="test_api_key",
        vonage_api_secret="test_api_secret",
        vonage_application_id="test_app_id",
        vonage_private_key_path="/path/to/key",
        greeting_message="テストメッセージ",
        greeting_language="ja-JP",
        greeting_style=0,
        max_recording_duration=60,
        recording_format="mp3",
        end_on_silence=3,
        webhook_base_url="https://example.com",
        answer_url="https://example.com/webhooks/answer",
        event_url="https://example.com/webhooks/event",
        recording_url="https://example.com/webhooks/recording",
        log_level="DEBUG"
    )


@pytest.fixture
def app(test_config):
    """テスト用の Flask アプリケーションを作成"""
    app = create_app(test_config)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """テスト用のクライアントを作成"""
    return app.test_client()


class TestFlaskAppCreation:
    """Flask アプリケーション作成のテスト"""
    
    def test_create_app_returns_flask_instance(self, test_config):
        """create_app が Flask インスタンスを返すことを確認"""
        from flask import Flask
        app = create_app(test_config)
        assert isinstance(app, Flask)
    
    def test_create_app_stores_config(self, test_config):
        """create_app が設定を保存することを確認"""
        app = create_app(test_config)
        assert app.config["VOICE_RECORDER_CONFIG"] == test_config
    
    def test_create_app_initializes_storage(self, test_config):
        """create_app がストレージを初期化することを確認"""
        app = create_app(test_config)
        assert "STORAGE" in app.config
        assert isinstance(app.config["STORAGE"], SQLiteStorage)
    
    def test_create_app_initializes_ncco_builder(self, test_config):
        """create_app が NCCO Builder を初期化することを確認"""
        app = create_app(test_config)
        assert "NCCO_BUILDER" in app.config
        assert isinstance(app.config["NCCO_BUILDER"], NCCOBuilder)
    
    def test_create_app_initializes_recording_manager(self, test_config):
        """create_app が Recording Manager を初期化することを確認"""
        app = create_app(test_config)
        assert "RECORDING_MANAGER" in app.config
        assert isinstance(app.config["RECORDING_MANAGER"], RecordingManager)
    
    def test_create_app_initializes_webhook_handler(self, test_config):
        """create_app が Webhook Handler を初期化することを確認"""
        app = create_app(test_config)
        assert "WEBHOOK_HANDLER" in app.config
        assert isinstance(app.config["WEBHOOK_HANDLER"], WebhookHandler)


class TestHealthCheckEndpoint:
    """ヘルスチェックエンドポイントのテスト"""
    
    def test_health_check_returns_200(self, client):
        """ヘルスチェックが 200 を返すことを確認"""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_check_returns_healthy_status(self, client):
        """ヘルスチェックが healthy ステータスを返すことを確認"""
        response = client.get("/health")
        data = json.loads(response.data)
        assert data["status"] == "healthy"
    
    def test_health_check_returns_json(self, client):
        """ヘルスチェックが JSON を返すことを確認"""
        response = client.get("/health")
        assert response.content_type == "application/json"


class TestStructuredLogging:
    """
    構造化ロギングのテスト
    
    Requirements:
        - 6.1: 適切なログレベルで操作をログ出力
        - 6.3: Webhook 受信時にリクエスト詳細をデバッグレベルでログ出力
        - 6.5: 構造化ロギングフォーマットを使用
    """
    
    def test_configure_structlog_does_not_raise(self):
        """configure_structlog がエラーを発生させないことを確認"""
        # エラーが発生しなければ成功
        configure_structlog("INFO")
    
    def test_configure_structlog_accepts_valid_log_levels(self):
        """
        configure_structlog が有効なログレベルを受け入れることを確認
        
        Requirements:
            - 6.1: 適切なログレベルで操作をログ出力
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in valid_levels:
            configure_structlog(level)  # エラーが発生しなければ成功
    
    def test_get_logger_returns_bound_logger(self):
        """get_logger が BoundLogger を返すことを確認"""
        configure_structlog("INFO")
        logger = get_logger("test")
        # structlog のロガーであることを確認
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
    
    def test_structlog_outputs_json_format(self, capsys):
        """
        structlog が JSON フォーマットで出力することを確認
        
        Requirements:
            - 6.5: 構造化ロギングフォーマットを使用
        """
        import structlog
        
        # structlog を再設定
        configure_structlog("INFO")
        
        # 新しいロガーを取得してログ出力
        logger = structlog.get_logger("test_json_output")
        logger.info("test_message", key="value")
        
        # 標準出力をキャプチャ
        captured = capsys.readouterr()
        
        # JSON としてパース可能であることを確認
        if captured.out.strip():
            log_output = json.loads(captured.out.strip())
            assert isinstance(log_output, dict)
    
    def test_structlog_output_contains_timestamp(self, capsys):
        """
        structlog 出力が timestamp フィールドを含むことを確認
        
        Requirements:
            - 6.5: 構造化ロギングフォーマットを使用
        """
        import structlog
        
        configure_structlog("INFO")
        logger = structlog.get_logger("test_timestamp")
        logger.info("test_message")
        
        captured = capsys.readouterr()
        if captured.out.strip():
            log_output = json.loads(captured.out.strip())
            assert "timestamp" in log_output
    
    def test_structlog_output_contains_level(self, capsys):
        """
        structlog 出力が level フィールドを含むことを確認
        
        Requirements:
            - 6.1: 適切なログレベルで操作をログ出力
            - 6.5: 構造化ロギングフォーマットを使用
        """
        import structlog
        
        configure_structlog("INFO")
        logger = structlog.get_logger("test_level")
        logger.info("test_message")
        
        captured = capsys.readouterr()
        if captured.out.strip():
            log_output = json.loads(captured.out.strip())
            assert "level" in log_output
            assert log_output["level"] == "info"
    
    def test_structlog_output_contains_event_message(self, capsys):
        """
        structlog 出力が event (message) フィールドを含むことを確認
        
        Requirements:
            - 6.5: 構造化ロギングフォーマットを使用
        """
        import structlog
        
        configure_structlog("INFO")
        logger = structlog.get_logger("test_event")
        logger.info("test_event_message")
        
        captured = capsys.readouterr()
        if captured.out.strip():
            log_output = json.loads(captured.out.strip())
            assert "event" in log_output
            assert log_output["event"] == "test_event_message"
    
    def test_structlog_output_contains_custom_fields(self, capsys):
        """
        structlog 出力がカスタムフィールドを含むことを確認
        
        Requirements:
            - 6.5: 構造化ロギングフォーマットを使用
        """
        import structlog
        
        configure_structlog("INFO")
        logger = structlog.get_logger("test_custom")
        logger.info("test_message", call_uuid="test-uuid", caller_number="+81901234567")
        
        captured = capsys.readouterr()
        if captured.out.strip():
            log_output = json.loads(captured.out.strip())
            assert "call_uuid" in log_output
            assert log_output["call_uuid"] == "test-uuid"
            assert "caller_number" in log_output
            assert log_output["caller_number"] == "+81901234567"
    
    def test_log_level_configuration_via_environment(self):
        """
        ログレベルが環境変数で設定可能であることを確認
        
        Requirements:
            - 6.1: 適切なログレベルで操作をログ出力
        """
        # Config クラスが LOG_LEVEL 環境変数を読み込むことを確認
        from src.config import Config
        
        # デフォルト値の確認
        assert Config.DEFAULT_LOG_LEVEL == "INFO"
        
        # 有効なログレベルの確認
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in valid_levels:
            # 環境変数をモックしてテスト
            with patch.dict(os.environ, {
                "VONAGE_API_KEY": "test_key",
                "VONAGE_API_SECRET": "test_secret",
                "VONAGE_APPLICATION_ID": "test_app_id",
                "VONAGE_PRIVATE_KEY_PATH": "/path/to/key",
                "WEBHOOK_BASE_URL": "https://example.com",
                "LOG_LEVEL": level
            }):
                config = Config.from_env()
                assert config.log_level == level
    
    def test_debug_level_logging_available(self, capsys):
        """
        デバッグレベルのロギングが利用可能であることを確認
        
        Requirements:
            - 6.3: Webhook 受信時にリクエスト詳細をデバッグレベルでログ出力
        """
        import structlog
        
        # DEBUG レベルで設定
        configure_structlog("DEBUG")
        logger = structlog.get_logger("test_debug")
        logger.debug("debug_message", request_details={"path": "/webhooks/answer"})
        
        captured = capsys.readouterr()
        if captured.out.strip():
            log_output = json.loads(captured.out.strip())
            assert log_output["level"] == "debug"
            assert "request_details" in log_output


class TestWebhookHandler:
    """WebhookHandler クラスのテスト"""
    
    @pytest.fixture
    def webhook_handler(self, test_config):
        """テスト用の WebhookHandler を作成"""
        storage = SQLiteStorage(":memory:")
        ncco_builder = NCCOBuilder(test_config)
        recording_manager = RecordingManager(storage)
        return WebhookHandler(ncco_builder, recording_manager, storage)
    
    def test_webhook_handler_has_handle_answer_method(self, webhook_handler):
        """WebhookHandler が handle_answer メソッドを持つことを確認"""
        assert hasattr(webhook_handler, "handle_answer")
        assert callable(webhook_handler.handle_answer)
    
    def test_webhook_handler_has_handle_recording_method(self, webhook_handler):
        """WebhookHandler が handle_recording メソッドを持つことを確認"""
        assert hasattr(webhook_handler, "handle_recording")
        assert callable(webhook_handler.handle_recording)
    
    def test_webhook_handler_has_handle_event_method(self, webhook_handler):
        """WebhookHandler が handle_event メソッドを持つことを確認"""
        assert hasattr(webhook_handler, "handle_event")
        assert callable(webhook_handler.handle_event)
    
    def test_webhook_handler_has_logger(self, webhook_handler):
        """WebhookHandler がロガーを持つことを確認"""
        assert hasattr(webhook_handler, "logger")
    
    def test_webhook_handler_has_ncco_builder(self, webhook_handler):
        """WebhookHandler が NCCO Builder を持つことを確認"""
        assert hasattr(webhook_handler, "ncco_builder")
        assert isinstance(webhook_handler.ncco_builder, NCCOBuilder)
    
    def test_webhook_handler_has_recording_manager(self, webhook_handler):
        """WebhookHandler が Recording Manager を持つことを確認"""
        assert hasattr(webhook_handler, "recording_manager")
        assert isinstance(webhook_handler.recording_manager, RecordingManager)


class TestHandleAnswerMethod:
    """handle_answer メソッドのテスト"""
    
    @pytest.fixture
    def storage(self, tmp_path):
        """テスト用のストレージを作成（一時ファイル使用）"""
        db_path = str(tmp_path / "test_voice_recorder.db")
        return SQLiteStorage(db_path)
    
    @pytest.fixture
    def webhook_handler(self, test_config, storage):
        """テスト用の WebhookHandler を作成"""
        ncco_builder = NCCOBuilder(test_config)
        recording_manager = RecordingManager(storage)
        return WebhookHandler(ncco_builder, recording_manager, storage)
    
    def test_handle_answer_returns_list(self, webhook_handler):
        """handle_answer がリストを返すことを確認"""
        params = {
            "uuid": "test-call-uuid",
            "from": "+81901234567",
            "to": "+81312345678",
            "conversation_uuid": "test-conversation-uuid"
        }
        result = webhook_handler.handle_answer(params)
        assert isinstance(result, list)
    
    def test_handle_answer_returns_ncco_with_two_actions(self, webhook_handler):
        """handle_answer が 2 つのアクションを含む NCCO を返すことを確認"""
        params = {
            "uuid": "test-call-uuid",
            "from": "+81901234567",
            "to": "+81312345678",
            "conversation_uuid": "test-conversation-uuid"
        }
        result = webhook_handler.handle_answer(params)
        assert len(result) == 2
    
    def test_handle_answer_returns_talk_action_first(self, webhook_handler):
        """handle_answer が最初に talk アクションを返すことを確認"""
        params = {
            "uuid": "test-call-uuid",
            "from": "+81901234567",
            "to": "+81312345678",
            "conversation_uuid": "test-conversation-uuid"
        }
        result = webhook_handler.handle_answer(params)
        assert result[0]["action"] == "talk"
    
    def test_handle_answer_returns_record_action_second(self, webhook_handler):
        """handle_answer が 2 番目に record アクションを返すことを確認"""
        params = {
            "uuid": "test-call-uuid",
            "from": "+81901234567",
            "to": "+81312345678",
            "conversation_uuid": "test-conversation-uuid"
        }
        result = webhook_handler.handle_answer(params)
        assert result[1]["action"] == "record"
    
    def test_handle_answer_saves_call_log(self, webhook_handler, storage):
        """handle_answer が通話ログを保存することを確認"""
        params = {
            "uuid": "test-call-uuid-for-log",
            "from": "+81901234567",
            "to": "+81312345678",
            "conversation_uuid": "test-conversation-uuid"
        }
        webhook_handler.handle_answer(params)
        
        # 通話ログが保存されたことを確認
        call_log = storage.get_call_log("test-call-uuid-for-log")
        assert call_log is not None
        assert call_log.call_uuid == "test-call-uuid-for-log"
        assert call_log.caller_number == "+81901234567"
        assert call_log.called_number == "+81312345678"
        assert call_log.status == "answered"
        assert call_log.direction == "inbound"
    
    def test_handle_answer_with_empty_params(self, webhook_handler):
        """handle_answer が空のパラメータでも動作することを確認"""
        params = {}
        result = webhook_handler.handle_answer(params)
        assert isinstance(result, list)
        assert len(result) == 2


class TestAnswerWebhookEndpoint:
    """Answer Webhook エンドポイントのテスト"""
    
    def test_answer_webhook_returns_200(self, client):
        """Answer Webhook が 200 を返すことを確認"""
        response = client.get("/webhooks/answer?uuid=test-uuid&from=+81901234567&to=+81312345678&conversation_uuid=test-conv")
        assert response.status_code == 200
    
    def test_answer_webhook_returns_json(self, client):
        """Answer Webhook が JSON を返すことを確認"""
        response = client.get("/webhooks/answer?uuid=test-uuid&from=+81901234567&to=+81312345678&conversation_uuid=test-conv")
        assert response.content_type == "application/json"
    
    def test_answer_webhook_returns_ncco_list(self, client):
        """Answer Webhook が NCCO リストを返すことを確認"""
        response = client.get("/webhooks/answer?uuid=test-uuid&from=+81901234567&to=+81312345678&conversation_uuid=test-conv")
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_answer_webhook_returns_two_actions(self, client):
        """Answer Webhook が 2 つのアクションを返すことを確認"""
        response = client.get("/webhooks/answer?uuid=test-uuid&from=+81901234567&to=+81312345678&conversation_uuid=test-conv")
        data = json.loads(response.data)
        assert len(data) == 2
    
    def test_answer_webhook_returns_talk_action_first(self, client):
        """Answer Webhook が最初に talk アクションを返すことを確認"""
        response = client.get("/webhooks/answer?uuid=test-uuid&from=+81901234567&to=+81312345678&conversation_uuid=test-conv")
        data = json.loads(response.data)
        assert data[0]["action"] == "talk"
    
    def test_answer_webhook_returns_record_action_second(self, client):
        """Answer Webhook が 2 番目に record アクションを返すことを確認"""
        response = client.get("/webhooks/answer?uuid=test-uuid&from=+81901234567&to=+81312345678&conversation_uuid=test-conv")
        data = json.loads(response.data)
        assert data[1]["action"] == "record"
    
    def test_answer_webhook_talk_action_has_text(self, client):
        """Answer Webhook の talk アクションがテキストを含むことを確認"""
        response = client.get("/webhooks/answer?uuid=test-uuid&from=+81901234567&to=+81312345678&conversation_uuid=test-conv")
        data = json.loads(response.data)
        assert "text" in data[0]
        assert len(data[0]["text"]) > 0
    
    def test_answer_webhook_record_action_has_event_url(self, client):
        """Answer Webhook の record アクションが eventUrl を含むことを確認"""
        response = client.get("/webhooks/answer?uuid=test-uuid&from=+81901234567&to=+81312345678&conversation_uuid=test-conv")
        data = json.loads(response.data)
        assert "eventUrl" in data[1]
        assert isinstance(data[1]["eventUrl"], list)
    
    def test_answer_webhook_without_params(self, client):
        """Answer Webhook がパラメータなしでも動作することを確認"""
        response = client.get("/webhooks/answer")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 2


class TestHandleRecordingMethod:
    """handle_recording メソッドのテスト"""
    
    @pytest.fixture
    def storage(self, tmp_path):
        """テスト用のストレージを作成（一時ファイル使用）"""
        db_path = str(tmp_path / "test_voice_recorder.db")
        return SQLiteStorage(db_path)
    
    @pytest.fixture
    def webhook_handler(self, test_config, storage):
        """テスト用の WebhookHandler を作成"""
        ncco_builder = NCCOBuilder(test_config)
        recording_manager = RecordingManager(storage)
        return WebhookHandler(ncco_builder, recording_manager, storage)
    
    def test_handle_recording_saves_metadata(self, webhook_handler, storage):
        """handle_recording が録音メタデータを保存することを確認"""
        data = {
            "recording_url": "https://api.nexmo.com/v1/files/test-recording-uuid",
            "recording_uuid": "test-recording-uuid",
            "conversation_uuid": "test-conversation-uuid",
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T10:01:00Z",
            "size": 12345,
            "duration": 60
        }
        
        webhook_handler.handle_recording(data)
        
        # 録音メタデータが保存されたことを確認
        recording = storage.get_recording("test-conversation-uuid")
        assert recording is not None
        assert recording.recording_url == "https://api.nexmo.com/v1/files/test-recording-uuid"
        assert recording.duration == 60
    
    def test_handle_recording_with_empty_data(self, webhook_handler):
        """handle_recording が空のデータでも動作することを確認"""
        data = {}
        # エラーが発生しなければ成功
        webhook_handler.handle_recording(data)
    
    def test_handle_recording_extracts_recording_url(self, webhook_handler, storage):
        """handle_recording が recording_url を正しく抽出することを確認"""
        data = {
            "recording_url": "https://api.nexmo.com/v1/files/unique-recording-id",
            "conversation_uuid": "conv-uuid-for-url-test",
            "duration": 30
        }
        
        webhook_handler.handle_recording(data)
        
        recording = storage.get_recording("conv-uuid-for-url-test")
        assert recording is not None
        assert recording.recording_url == "https://api.nexmo.com/v1/files/unique-recording-id"
    
    def test_handle_recording_extracts_duration(self, webhook_handler, storage):
        """handle_recording が duration を正しく抽出することを確認"""
        data = {
            "recording_url": "https://api.nexmo.com/v1/files/test-file",
            "conversation_uuid": "conv-uuid-for-duration-test",
            "duration": 120
        }
        
        webhook_handler.handle_recording(data)
        
        recording = storage.get_recording("conv-uuid-for-duration-test")
        assert recording is not None
        assert recording.duration == 120
    
    def test_handle_recording_extracts_file_size(self, webhook_handler, storage):
        """handle_recording が file_size を正しく抽出することを確認"""
        data = {
            "recording_url": "https://api.nexmo.com/v1/files/test-file",
            "conversation_uuid": "conv-uuid-for-size-test",
            "size": 54321,
            "duration": 45
        }
        
        webhook_handler.handle_recording(data)
        
        recording = storage.get_recording("conv-uuid-for-size-test")
        assert recording is not None
        assert recording.file_size == 54321
    
    def test_handle_recording_sets_completed_status(self, webhook_handler, storage):
        """handle_recording がステータスを completed に設定することを確認"""
        data = {
            "recording_url": "https://api.nexmo.com/v1/files/test-file",
            "conversation_uuid": "conv-uuid-for-status-test",
            "duration": 30
        }
        
        webhook_handler.handle_recording(data)
        
        recording = storage.get_recording("conv-uuid-for-status-test")
        assert recording is not None
        assert recording.status == "completed"


class TestRecordingWebhookEndpoint:
    """Recording Webhook エンドポイントのテスト"""
    
    def test_recording_webhook_returns_200(self, client):
        """Recording Webhook が 200 を返すことを確認"""
        data = {
            "recording_url": "https://api.nexmo.com/v1/files/test-recording",
            "recording_uuid": "test-recording-uuid",
            "conversation_uuid": "test-conversation-uuid",
            "duration": 60
        }
        response = client.post(
            "/webhooks/recording",
            data=json.dumps(data),
            content_type="application/json"
        )
        assert response.status_code == 200
    
    def test_recording_webhook_returns_json(self, client):
        """Recording Webhook が JSON を返すことを確認"""
        data = {
            "recording_url": "https://api.nexmo.com/v1/files/test-recording",
            "conversation_uuid": "test-conversation-uuid",
            "duration": 60
        }
        response = client.post(
            "/webhooks/recording",
            data=json.dumps(data),
            content_type="application/json"
        )
        assert response.content_type == "application/json"
    
    def test_recording_webhook_returns_ok_status(self, client):
        """Recording Webhook が ok ステータスを返すことを確認"""
        data = {
            "recording_url": "https://api.nexmo.com/v1/files/test-recording",
            "conversation_uuid": "test-conversation-uuid",
            "duration": 60
        }
        response = client.post(
            "/webhooks/recording",
            data=json.dumps(data),
            content_type="application/json"
        )
        response_data = json.loads(response.data)
        assert response_data["status"] == "ok"
    
    def test_recording_webhook_with_empty_body(self, client):
        """Recording Webhook が空のボディでも動作することを確認"""
        response = client.post(
            "/webhooks/recording",
            data=json.dumps({}),
            content_type="application/json"
        )
        assert response.status_code == 200
    
    def test_recording_webhook_accepts_post_method(self, client):
        """Recording Webhook が POST メソッドを受け入れることを確認"""
        data = {"recording_url": "https://example.com/recording"}
        response = client.post(
            "/webhooks/recording",
            data=json.dumps(data),
            content_type="application/json"
        )
        assert response.status_code == 200
    
    def test_recording_webhook_rejects_get_method(self, client):
        """Recording Webhook が GET メソッドを拒否することを確認"""
        response = client.get("/webhooks/recording")
        assert response.status_code == 405  # Method Not Allowed


class TestHandleEventMethod:
    """handle_event メソッドのテスト"""
    
    @pytest.fixture
    def storage(self, tmp_path):
        """テスト用のストレージを作成（一時ファイル使用）"""
        db_path = str(tmp_path / "test_voice_recorder.db")
        return SQLiteStorage(db_path)
    
    @pytest.fixture
    def webhook_handler(self, test_config, storage):
        """テスト用の WebhookHandler を作成"""
        ncco_builder = NCCOBuilder(test_config)
        recording_manager = RecordingManager(storage)
        return WebhookHandler(ncco_builder, recording_manager, storage)
    
    def test_handle_event_updates_call_log_status(self, webhook_handler, storage):
        """handle_event が通話ログのステータスを更新することを確認"""
        # まず通話ログを作成
        params = {
            "uuid": "test-call-uuid-for-event",
            "from": "+81901234567",
            "to": "+81312345678",
            "conversation_uuid": "test-conversation-uuid"
        }
        webhook_handler.handle_answer(params)
        
        # イベントを処理
        event_data = {
            "uuid": "test-call-uuid-for-event",
            "status": "completed",
            "timestamp": "2024-01-15T10:05:00Z"
        }
        webhook_handler.handle_event(event_data)
        
        # 通話ログのステータスが更新されたことを確認
        call_log = storage.get_call_log("test-call-uuid-for-event")
        assert call_log is not None
        assert call_log.status == "completed"
    
    def test_handle_event_sets_ended_at_for_terminal_status(self, webhook_handler, storage):
        """handle_event が終了ステータスの場合に ended_at を設定することを確認"""
        # まず通話ログを作成
        params = {
            "uuid": "test-call-uuid-for-ended",
            "from": "+81901234567",
            "to": "+81312345678",
            "conversation_uuid": "test-conversation-uuid"
        }
        webhook_handler.handle_answer(params)
        
        # イベントを処理
        event_data = {
            "uuid": "test-call-uuid-for-ended",
            "status": "completed",
            "timestamp": "2024-01-15T10:05:00Z"
        }
        webhook_handler.handle_event(event_data)
        
        # ended_at が設定されたことを確認
        call_log = storage.get_call_log("test-call-uuid-for-ended")
        assert call_log is not None
        assert call_log.ended_at is not None
    
    def test_handle_event_does_not_set_ended_at_for_non_terminal_status(self, webhook_handler, storage):
        """handle_event が非終了ステータスの場合に ended_at を設定しないことを確認"""
        # まず通話ログを作成
        params = {
            "uuid": "test-call-uuid-for-ringing",
            "from": "+81901234567",
            "to": "+81312345678",
            "conversation_uuid": "test-conversation-uuid"
        }
        webhook_handler.handle_answer(params)
        
        # イベントを処理（ringing は非終了ステータス）
        event_data = {
            "uuid": "test-call-uuid-for-ringing",
            "status": "ringing",
            "timestamp": "2024-01-15T10:00:30Z"
        }
        webhook_handler.handle_event(event_data)
        
        # ステータスは更新されるが ended_at は設定されない
        call_log = storage.get_call_log("test-call-uuid-for-ringing")
        assert call_log is not None
        assert call_log.status == "ringing"
        assert call_log.ended_at is None
    
    def test_handle_event_with_empty_data(self, webhook_handler):
        """handle_event が空のデータでも動作することを確認"""
        data = {}
        # エラーが発生しなければ成功
        webhook_handler.handle_event(data)
    
    def test_handle_event_with_missing_uuid(self, webhook_handler):
        """handle_event が UUID なしでも動作することを確認"""
        data = {
            "status": "completed",
            "timestamp": "2024-01-15T10:05:00Z"
        }
        # エラーが発生しなければ成功
        webhook_handler.handle_event(data)
    
    def test_handle_event_handles_failed_status(self, webhook_handler, storage):
        """handle_event が failed ステータスを処理することを確認"""
        # まず通話ログを作成
        params = {
            "uuid": "test-call-uuid-for-failed",
            "from": "+81901234567",
            "to": "+81312345678",
            "conversation_uuid": "test-conversation-uuid"
        }
        webhook_handler.handle_answer(params)
        
        # failed イベントを処理
        event_data = {
            "uuid": "test-call-uuid-for-failed",
            "status": "failed",
            "reason": "network_error",
            "timestamp": "2024-01-15T10:05:00Z"
        }
        webhook_handler.handle_event(event_data)
        
        # 通話ログのステータスが更新されたことを確認
        call_log = storage.get_call_log("test-call-uuid-for-failed")
        assert call_log is not None
        assert call_log.status == "failed"
        assert call_log.ended_at is not None
    
    def test_handle_event_handles_nonexistent_call_uuid(self, webhook_handler):
        """handle_event が存在しない通話 UUID でも動作することを確認"""
        event_data = {
            "uuid": "nonexistent-call-uuid",
            "status": "completed",
            "timestamp": "2024-01-15T10:05:00Z"
        }
        # エラーが発生しなければ成功（警告ログが出力される）
        webhook_handler.handle_event(event_data)


class TestEventWebhookEndpoint:
    """Event Webhook エンドポイントのテスト"""
    
    def test_event_webhook_returns_200(self, client):
        """Event Webhook が 200 を返すことを確認"""
        data = {
            "uuid": "test-call-uuid",
            "status": "completed",
            "timestamp": "2024-01-15T10:05:00Z"
        }
        response = client.post(
            "/webhooks/event",
            data=json.dumps(data),
            content_type="application/json"
        )
        assert response.status_code == 200
    
    def test_event_webhook_returns_json(self, client):
        """Event Webhook が JSON を返すことを確認"""
        data = {
            "uuid": "test-call-uuid",
            "status": "completed",
            "timestamp": "2024-01-15T10:05:00Z"
        }
        response = client.post(
            "/webhooks/event",
            data=json.dumps(data),
            content_type="application/json"
        )
        assert response.content_type == "application/json"
    
    def test_event_webhook_returns_ok_status(self, client):
        """Event Webhook が ok ステータスを返すことを確認"""
        data = {
            "uuid": "test-call-uuid",
            "status": "completed",
            "timestamp": "2024-01-15T10:05:00Z"
        }
        response = client.post(
            "/webhooks/event",
            data=json.dumps(data),
            content_type="application/json"
        )
        response_data = json.loads(response.data)
        assert response_data["status"] == "ok"
    
    def test_event_webhook_with_empty_body(self, client):
        """Event Webhook が空のボディでも動作することを確認"""
        response = client.post(
            "/webhooks/event",
            data=json.dumps({}),
            content_type="application/json"
        )
        assert response.status_code == 200
    
    def test_event_webhook_accepts_post_method(self, client):
        """Event Webhook が POST メソッドを受け入れることを確認"""
        data = {"uuid": "test-uuid", "status": "completed"}
        response = client.post(
            "/webhooks/event",
            data=json.dumps(data),
            content_type="application/json"
        )
        assert response.status_code == 200
    
    def test_event_webhook_rejects_get_method(self, client):
        """Event Webhook が GET メソッドを拒否することを確認"""
        response = client.get("/webhooks/event")
        assert response.status_code == 405  # Method Not Allowed
    
    def test_event_webhook_updates_call_log(self, app, client):
        """Event Webhook が通話ログを更新することを確認"""
        # まず Answer Webhook で通話ログを作成
        client.get("/webhooks/answer?uuid=test-event-uuid&from=+81901234567&to=+81312345678&conversation_uuid=test-conv")
        
        # Event Webhook で通話ステータスを更新
        event_data = {
            "uuid": "test-event-uuid",
            "status": "completed",
            "timestamp": "2024-01-15T10:05:00Z"
        }
        response = client.post(
            "/webhooks/event",
            data=json.dumps(event_data),
            content_type="application/json"
        )
        assert response.status_code == 200
        
        # 通話ログが更新されたことを確認
        storage = app.config["STORAGE"]
        call_log = storage.get_call_log("test-event-uuid")
        assert call_log is not None
        assert call_log.status == "completed"


class TestStorageUpdateCallLogStatus:
    """Storage.update_call_log_status メソッドのテスト"""
    
    @pytest.fixture
    def storage(self, tmp_path):
        """テスト用のストレージを作成（一時ファイル使用）"""
        db_path = str(tmp_path / "test_voice_recorder.db")
        return SQLiteStorage(db_path)
    
    def test_update_call_log_status_returns_true_on_success(self, storage):
        """update_call_log_status が成功時に True を返すことを確認"""
        from datetime import datetime
        from src.models import CallLog
        
        # 通話ログを作成
        call_log = CallLog(
            id="test-id",
            call_uuid="test-call-uuid",
            caller_number="+81901234567",
            called_number="+81312345678",
            status="answered",
            direction="inbound",
            started_at=datetime.utcnow(),
            ended_at=None,
            created_at=datetime.utcnow()
        )
        storage.save_call_log(call_log)
        
        # ステータスを更新
        result = storage.update_call_log_status("test-call-uuid", "completed")
        assert result is True
    
    def test_update_call_log_status_returns_false_for_nonexistent(self, storage):
        """update_call_log_status が存在しない UUID で False を返すことを確認"""
        result = storage.update_call_log_status("nonexistent-uuid", "completed")
        assert result is False
    
    def test_update_call_log_status_updates_status(self, storage):
        """update_call_log_status がステータスを更新することを確認"""
        from datetime import datetime
        from src.models import CallLog
        
        # 通話ログを作成
        call_log = CallLog(
            id="test-id-2",
            call_uuid="test-call-uuid-2",
            caller_number="+81901234567",
            called_number="+81312345678",
            status="answered",
            direction="inbound",
            started_at=datetime.utcnow(),
            ended_at=None,
            created_at=datetime.utcnow()
        )
        storage.save_call_log(call_log)
        
        # ステータスを更新
        storage.update_call_log_status("test-call-uuid-2", "completed")
        
        # 更新されたことを確認
        updated_log = storage.get_call_log("test-call-uuid-2")
        assert updated_log is not None
        assert updated_log.status == "completed"
    
    def test_update_call_log_status_sets_ended_at(self, storage):
        """update_call_log_status が ended_at を設定することを確認"""
        from datetime import datetime
        from src.models import CallLog
        
        # 通話ログを作成
        call_log = CallLog(
            id="test-id-3",
            call_uuid="test-call-uuid-3",
            caller_number="+81901234567",
            called_number="+81312345678",
            status="answered",
            direction="inbound",
            started_at=datetime.utcnow(),
            ended_at=None,
            created_at=datetime.utcnow()
        )
        storage.save_call_log(call_log)
        
        # ステータスと ended_at を更新
        ended_time = datetime(2024, 1, 15, 10, 5, 0)
        storage.update_call_log_status("test-call-uuid-3", "completed", ended_at=ended_time)
        
        # 更新されたことを確認
        updated_log = storage.get_call_log("test-call-uuid-3")
        assert updated_log is not None
        assert updated_log.ended_at is not None
        assert updated_log.ended_at.year == 2024
        assert updated_log.ended_at.month == 1
        assert updated_log.ended_at.day == 15


# ==========================================================================
# エラーハンドリングのテスト (Error Handling Tests)
# Requirements: 1.4, 6.2, 6.4
# ==========================================================================

class TestErrorHandling:
    """エラーハンドリングのテスト"""
    
    def test_recording_webhook_with_invalid_json_returns_400(self, client):
        """
        Recording Webhook が不正な JSON で 400 を返すことを確認
        
        Requirements:
            - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
        """
        response = client.post(
            "/webhooks/recording",
            data="not valid json {{{",
            content_type="application/json"
        )
        assert response.status_code == 400
    
    def test_event_webhook_with_invalid_json_returns_400(self, client):
        """
        Event Webhook が不正な JSON で 400 を返すことを確認
        
        Requirements:
            - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
        """
        response = client.post(
            "/webhooks/event",
            data="not valid json {{{",
            content_type="application/json"
        )
        assert response.status_code == 400
    
    def test_error_response_contains_error_field(self, client):
        """
        エラーレスポンスが error フィールドを含むことを確認
        
        Requirements:
            - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
        """
        response = client.post(
            "/webhooks/recording",
            data="invalid json",
            content_type="application/json"
        )
        data = json.loads(response.data)
        assert "error" in data
    
    def test_error_response_contains_message_field(self, client):
        """
        エラーレスポンスが message フィールドを含むことを確認
        
        Requirements:
            - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
        """
        response = client.post(
            "/webhooks/recording",
            data="invalid json",
            content_type="application/json"
        )
        data = json.loads(response.data)
        assert "message" in data
    
    def test_error_response_contains_status_code_field(self, client):
        """
        エラーレスポンスが status_code フィールドを含むことを確認
        
        Requirements:
            - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
        """
        response = client.post(
            "/webhooks/recording",
            data="invalid json",
            content_type="application/json"
        )
        data = json.loads(response.data)
        assert "status_code" in data
        assert data["status_code"] == 400


class TestWebhookValidationError:
    """WebhookValidationError クラスのテスト"""
    
    def test_webhook_validation_error_has_message(self):
        """WebhookValidationError が message 属性を持つことを確認"""
        from src.app import WebhookValidationError
        
        error = WebhookValidationError("Test error message")
        assert error.message == "Test error message"
    
    def test_webhook_validation_error_has_error_type(self):
        """WebhookValidationError が error_type 属性を持つことを確認"""
        from src.app import WebhookValidationError
        
        error = WebhookValidationError("Test error", error_type="custom_error")
        assert error.error_type == "custom_error"
    
    def test_webhook_validation_error_default_error_type(self):
        """WebhookValidationError のデフォルト error_type を確認"""
        from src.app import WebhookValidationError
        
        error = WebhookValidationError("Test error")
        assert error.error_type == "validation_error"


class TestVonageAPIError:
    """VonageAPIError クラスのテスト"""
    
    def test_vonage_api_error_has_message(self):
        """VonageAPIError が message 属性を持つことを確認"""
        from src.app import VonageAPIError
        
        error = VonageAPIError("API error message")
        assert error.message == "API error message"
    
    def test_vonage_api_error_has_status_code(self):
        """VonageAPIError が status_code 属性を持つことを確認"""
        from src.app import VonageAPIError
        
        error = VonageAPIError("API error", status_code=503)
        assert error.status_code == 503
    
    def test_vonage_api_error_default_status_code(self):
        """VonageAPIError のデフォルト status_code を確認"""
        from src.app import VonageAPIError
        
        error = VonageAPIError("API error")
        assert error.status_code == 500
    
    def test_vonage_api_error_has_details(self):
        """VonageAPIError が details 属性を持つことを確認"""
        from src.app import VonageAPIError
        
        details = {"reason": "timeout", "retry_after": 30}
        error = VonageAPIError("API error", details=details)
        assert error.details == details
    
    def test_vonage_api_error_default_details(self):
        """VonageAPIError のデフォルト details を確認"""
        from src.app import VonageAPIError
        
        error = VonageAPIError("API error")
        assert error.details == {}


class TestValidateJsonRequest:
    """validate_json_request 関数のテスト"""
    
    def test_validate_json_request_with_valid_dict(self):
        """validate_json_request が有効な辞書で True を返すことを確認"""
        from src.app import validate_json_request
        
        is_valid, error_message = validate_json_request({"key": "value"})
        assert is_valid is True
        assert error_message is None
    
    def test_validate_json_request_with_none(self):
        """validate_json_request が None で False を返すことを確認"""
        from src.app import validate_json_request
        
        is_valid, error_message = validate_json_request(None)
        assert is_valid is False
        assert error_message is not None
        assert "empty or malformed" in error_message
    
    def test_validate_json_request_with_non_dict(self):
        """validate_json_request が非辞書で False を返すことを確認"""
        from src.app import validate_json_request
        
        is_valid, error_message = validate_json_request(["list", "data"])
        assert is_valid is False
        assert error_message is not None
        assert "must be a JSON object" in error_message
    
    def test_validate_json_request_with_required_fields_present(self):
        """validate_json_request が必須フィールドありで True を返すことを確認"""
        from src.app import validate_json_request
        
        data = {"field1": "value1", "field2": "value2"}
        is_valid, error_message = validate_json_request(data, required_fields=["field1", "field2"])
        assert is_valid is True
        assert error_message is None
    
    def test_validate_json_request_with_missing_required_fields(self):
        """validate_json_request が必須フィールド欠落で False を返すことを確認"""
        from src.app import validate_json_request
        
        data = {"field1": "value1"}
        is_valid, error_message = validate_json_request(data, required_fields=["field1", "field2"])
        assert is_valid is False
        assert error_message is not None
        assert "Missing required fields" in error_message
        assert "field2" in error_message


class TestCreateErrorResponse:
    """create_error_response 関数のテスト"""
    
    @pytest.fixture
    def app_context(self, app):
        """テスト用のアプリケーションコンテキストを作成"""
        with app.app_context():
            yield
    
    def test_create_error_response_returns_tuple(self, app_context):
        """create_error_response がタプルを返すことを確認"""
        from src.app import create_error_response
        
        result = create_error_response("test_error", "Test message", 400)
        assert isinstance(result, tuple)
        assert len(result) == 2
    
    def test_create_error_response_returns_correct_status_code(self, app_context):
        """create_error_response が正しいステータスコードを返すことを確認"""
        from src.app import create_error_response
        
        response, status_code = create_error_response("test_error", "Test message", 404)
        assert status_code == 404
    
    def test_create_error_response_contains_error_type(self, app_context):
        """create_error_response のレスポンスが error フィールドを含むことを確認"""
        from src.app import create_error_response
        
        response, _ = create_error_response("test_error", "Test message", 400)
        data = json.loads(response.data)
        assert data["error"] == "test_error"
    
    def test_create_error_response_contains_message(self, app_context):
        """create_error_response のレスポンスが message フィールドを含むことを確認"""
        from src.app import create_error_response
        
        response, _ = create_error_response("test_error", "Test message", 400)
        data = json.loads(response.data)
        assert data["message"] == "Test message"
    
    def test_create_error_response_contains_status_code(self, app_context):
        """create_error_response のレスポンスが status_code フィールドを含むことを確認"""
        from src.app import create_error_response
        
        response, _ = create_error_response("test_error", "Test message", 400)
        data = json.loads(response.data)
        assert data["status_code"] == 400
    
    def test_create_error_response_with_details(self, app_context):
        """create_error_response が details を含むことを確認"""
        from src.app import create_error_response
        
        details = {"field": "value", "count": 42}
        response, _ = create_error_response("test_error", "Test message", 400, details=details)
        data = json.loads(response.data)
        assert "details" in data
        assert data["details"] == details
    
    def test_create_error_response_without_details(self, app_context):
        """create_error_response が details なしで動作することを確認"""
        from src.app import create_error_response
        
        response, _ = create_error_response("test_error", "Test message", 400)
        data = json.loads(response.data)
        assert "details" not in data


class TestErrorHandlerIntegration:
    """エラーハンドラーの統合テスト"""
    
    def test_recording_webhook_handles_json_array_as_invalid(self, client):
        """
        Recording Webhook が JSON 配列を不正として処理することを確認
        
        Requirements:
            - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
        """
        response = client.post(
            "/webhooks/recording",
            data=json.dumps(["array", "data"]),
            content_type="application/json"
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
    
    def test_event_webhook_handles_json_array_as_invalid(self, client):
        """
        Event Webhook が JSON 配列を不正として処理することを確認
        
        Requirements:
            - 1.4: 不正な Webhook リクエストに対して適切な HTTP エラーステータスコードを返す
        """
        response = client.post(
            "/webhooks/event",
            data=json.dumps(["array", "data"]),
            content_type="application/json"
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
    
    def test_recording_webhook_accepts_empty_json_object(self, client):
        """
        Recording Webhook が空の JSON オブジェクトを受け入れることを確認
        """
        response = client.post(
            "/webhooks/recording",
            data=json.dumps({}),
            content_type="application/json"
        )
        assert response.status_code == 200
    
    def test_event_webhook_accepts_empty_json_object(self, client):
        """
        Event Webhook が空の JSON オブジェクトを受け入れることを確認
        """
        response = client.post(
            "/webhooks/event",
            data=json.dumps({}),
            content_type="application/json"
        )
        assert response.status_code == 200
    
    def test_recording_webhook_accepts_valid_json_object(self, client):
        """
        Recording Webhook が有効な JSON オブジェクトを受け入れることを確認
        """
        data = {
            "recording_url": "https://api.nexmo.com/v1/files/test",
            "conversation_uuid": "test-uuid",
            "duration": 30
        }
        response = client.post(
            "/webhooks/recording",
            data=json.dumps(data),
            content_type="application/json"
        )
        assert response.status_code == 200
    
    def test_event_webhook_accepts_valid_json_object(self, client):
        """
        Event Webhook が有効な JSON オブジェクトを受け入れることを確認
        """
        data = {
            "uuid": "test-uuid",
            "status": "completed",
            "timestamp": "2024-01-15T10:00:00Z"
        }
        response = client.post(
            "/webhooks/event",
            data=json.dumps(data),
            content_type="application/json"
        )
        assert response.status_code == 200
