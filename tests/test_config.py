"""
Config クラスのユニットテスト

Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6 の検証
"""

import os
import pytest
from unittest import mock

from src.config import Config, ConfigurationError


class TestConfigFromEnv:
    """Config.from_env() メソッドのテスト"""
    
    @pytest.fixture
    def valid_env_vars(self):
        """有効な環境変数のセット"""
        return {
            "VONAGE_API_KEY": "test_api_key",
            "VONAGE_API_SECRET": "test_api_secret",
            "VONAGE_APPLICATION_ID": "test_app_id",
            "VONAGE_PRIVATE_KEY_PATH": "/path/to/private.key",
            "WEBHOOK_BASE_URL": "https://example.com",
        }
    
    def test_from_env_with_valid_required_vars(self, valid_env_vars):
        """
        正常系: 必須環境変数が設定されている場合、Configが正しく作成される
        Requirements: 5.1, 5.2, 5.5
        """
        with mock.patch.dict(os.environ, valid_env_vars, clear=True):
            config = Config.from_env()
            
            assert config.vonage_api_key == "test_api_key"
            assert config.vonage_api_secret == "test_api_secret"
            assert config.vonage_application_id == "test_app_id"
            assert config.vonage_private_key_path == "/path/to/private.key"
            assert config.webhook_base_url == "https://example.com"
    
    def test_from_env_generates_webhook_urls(self, valid_env_vars):
        """
        正常系: WEBHOOK_BASE_URLからWebhook URLが自動生成される
        Requirements: 5.5
        """
        with mock.patch.dict(os.environ, valid_env_vars, clear=True):
            config = Config.from_env()
            
            assert config.answer_url == "https://example.com/webhooks/answer"
            assert config.event_url == "https://example.com/webhooks/event"
            assert config.recording_url == "https://example.com/webhooks/recording"
    
    def test_from_env_uses_default_greeting(self, valid_env_vars):
        """
        正常系: GREETING_MESSAGEが未設定の場合、日本語デフォルトが使用される
        Requirements: 5.3
        """
        with mock.patch.dict(os.environ, valid_env_vars, clear=True):
            config = Config.from_env()
            
            expected_greeting = "お電話ありがとうございます。ただいま電話に出ることができません。発信音の後にメッセージをお残しください。"
            assert config.greeting_message == expected_greeting
            assert config.greeting_language == "ja-JP"
            assert config.greeting_style == 0
    
    def test_from_env_uses_custom_greeting(self, valid_env_vars):
        """
        正常系: GREETING_MESSAGEが設定されている場合、カスタムメッセージが使用される
        Requirements: 5.3
        """
        env_vars = {
            **valid_env_vars,
            "GREETING_MESSAGE": "カスタムメッセージです",
            "GREETING_LANGUAGE": "en-US",
            "GREETING_STYLE": "1",
        }
        with mock.patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()
            
            assert config.greeting_message == "カスタムメッセージです"
            assert config.greeting_language == "en-US"
            assert config.greeting_style == 1
    
    def test_from_env_uses_default_recording_settings(self, valid_env_vars):
        """
        正常系: 録音設定が未設定の場合、デフォルト値が使用される
        Requirements: 5.4
        """
        with mock.patch.dict(os.environ, valid_env_vars, clear=True):
            config = Config.from_env()
            
            assert config.max_recording_duration == 60
            assert config.recording_format == "mp3"
            assert config.end_on_silence == 3
    
    def test_from_env_uses_custom_recording_settings(self, valid_env_vars):
        """
        正常系: 録音設定がカスタマイズされている場合、その値が使用される
        Requirements: 5.4
        """
        env_vars = {
            **valid_env_vars,
            "MAX_RECORDING_DURATION": "120",
            "RECORDING_FORMAT": "wav",
            "END_ON_SILENCE": "5",
        }
        with mock.patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()
            
            assert config.max_recording_duration == 120
            assert config.recording_format == "wav"
            assert config.end_on_silence == 5
    
    def test_from_env_uses_default_log_level(self, valid_env_vars):
        """
        正常系: LOG_LEVELが未設定の場合、INFOがデフォルト
        """
        with mock.patch.dict(os.environ, valid_env_vars, clear=True):
            config = Config.from_env()
            
            assert config.log_level == "INFO"
    
    def test_from_env_custom_webhook_urls_override_generated(self, valid_env_vars):
        """
        正常系: 個別のWebhook URLが設定されている場合、それが優先される
        Requirements: 5.5
        """
        env_vars = {
            **valid_env_vars,
            "ANSWER_URL": "https://custom.com/answer",
            "EVENT_URL": "https://custom.com/event",
            "RECORDING_URL": "https://custom.com/recording",
        }
        with mock.patch.dict(os.environ, env_vars, clear=True):
            config = Config.from_env()
            
            assert config.answer_url == "https://custom.com/answer"
            assert config.event_url == "https://custom.com/event"
            assert config.recording_url == "https://custom.com/recording"


class TestConfigValidation:
    """Config.validate() メソッドのテスト"""
    
    def test_validate_missing_api_key(self):
        """
        エラー系: VONAGE_API_KEYが欠落している場合、エラーが発生する
        Requirements: 5.2, 5.6
        """
        with mock.patch.dict(os.environ, {
            "VONAGE_API_SECRET": "secret",
            "VONAGE_APPLICATION_ID": "app_id",
            "VONAGE_PRIVATE_KEY_PATH": "/path/to/key",
            "WEBHOOK_BASE_URL": "https://example.com",
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config.from_env()
            
            assert "VONAGE_API_KEY" in str(exc_info.value)
    
    def test_validate_missing_api_secret(self):
        """
        エラー系: VONAGE_API_SECRETが欠落している場合、エラーが発生する
        Requirements: 5.2, 5.6
        """
        with mock.patch.dict(os.environ, {
            "VONAGE_API_KEY": "key",
            "VONAGE_APPLICATION_ID": "app_id",
            "VONAGE_PRIVATE_KEY_PATH": "/path/to/key",
            "WEBHOOK_BASE_URL": "https://example.com",
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config.from_env()
            
            assert "VONAGE_API_SECRET" in str(exc_info.value)
    
    def test_validate_missing_multiple_required_fields(self):
        """
        エラー系: 複数の必須フィールドが欠落している場合、すべてがエラーメッセージに含まれる
        Requirements: 5.6
        """
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config.from_env()
            
            error_message = str(exc_info.value)
            assert "VONAGE_API_KEY" in error_message
            assert "VONAGE_API_SECRET" in error_message
            assert "VONAGE_APPLICATION_ID" in error_message
            assert "VONAGE_PRIVATE_KEY_PATH" in error_message
            assert "WEBHOOK_BASE_URL" in error_message
    
    def test_validate_missing_webhook_base_url(self):
        """
        エラー系: WEBHOOK_BASE_URLが欠落している場合、エラーが発生する
        Requirements: 5.5, 5.6
        """
        with mock.patch.dict(os.environ, {
            "VONAGE_API_KEY": "key",
            "VONAGE_API_SECRET": "secret",
            "VONAGE_APPLICATION_ID": "app_id",
            "VONAGE_PRIVATE_KEY_PATH": "/path/to/key",
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config.from_env()
            
            assert "WEBHOOK_BASE_URL" in str(exc_info.value)
    
    def test_validate_invalid_max_recording_duration(self):
        """
        エラー系: MAX_RECORDING_DURATIONが0以下の場合、エラーが発生する
        """
        with mock.patch.dict(os.environ, {
            "VONAGE_API_KEY": "key",
            "VONAGE_API_SECRET": "secret",
            "VONAGE_APPLICATION_ID": "app_id",
            "VONAGE_PRIVATE_KEY_PATH": "/path/to/key",
            "WEBHOOK_BASE_URL": "https://example.com",
            "MAX_RECORDING_DURATION": "0",
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config.from_env()
            
            assert "MAX_RECORDING_DURATION" in str(exc_info.value)
    
    def test_validate_invalid_recording_format(self):
        """
        エラー系: RECORDING_FORMATが無効な場合、エラーが発生する
        """
        with mock.patch.dict(os.environ, {
            "VONAGE_API_KEY": "key",
            "VONAGE_API_SECRET": "secret",
            "VONAGE_APPLICATION_ID": "app_id",
            "VONAGE_PRIVATE_KEY_PATH": "/path/to/key",
            "WEBHOOK_BASE_URL": "https://example.com",
            "RECORDING_FORMAT": "invalid_format",
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config.from_env()
            
            assert "RECORDING_FORMAT" in str(exc_info.value)
    
    def test_validate_invalid_log_level(self):
        """
        エラー系: LOG_LEVELが無効な場合、エラーが発生する
        """
        with mock.patch.dict(os.environ, {
            "VONAGE_API_KEY": "key",
            "VONAGE_API_SECRET": "secret",
            "VONAGE_APPLICATION_ID": "app_id",
            "VONAGE_PRIVATE_KEY_PATH": "/path/to/key",
            "WEBHOOK_BASE_URL": "https://example.com",
            "LOG_LEVEL": "INVALID",
        }, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config.from_env()
            
            assert "LOG_LEVEL" in str(exc_info.value)


class TestConfigErrorMessages:
    """エラーメッセージの明確さのテスト"""
    
    def test_error_message_is_clear_and_actionable(self):
        """
        エラーメッセージが明確で、どの環境変数を設定すべきか分かる
        Requirements: 5.6
        """
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config.from_env()
            
            error_message = str(exc_info.value)
            # エラーメッセージが日本語で明確であること
            assert "必須の設定が欠落しています" in error_message
            assert "環境変数を設定してください" in error_message
