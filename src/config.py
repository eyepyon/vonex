"""
設定管理モジュール (Configuration Management Module)

環境変数からアプリケーション設定を読み込み、検証を行います。
"""

from dataclasses import dataclass, field
from typing import Optional
import os


class ConfigurationError(Exception):
    """設定エラー例外クラス"""
    pass


@dataclass
class Config:
    """
    アプリケーション設定
    
    環境変数から設定を読み込み、必須設定のバリデーションを行います。
    """
    # Vonage API認証情報 (必須)
    vonage_api_key: str
    vonage_api_secret: str
    vonage_application_id: str
    vonage_private_key_path: str
    
    # 音声アナウンス設定
    greeting_message: str
    greeting_language: str
    greeting_style: int
    
    # 録音設定
    max_recording_duration: int
    recording_format: str
    end_on_silence: int
    
    # Webhook URL設定
    webhook_base_url: str
    answer_url: str
    event_url: str
    recording_url: str
    
    # ロギング設定
    log_level: str
    
    # 音楽生成設定（オプション）
    openai_api_key: Optional[str]
    udio_api_key: Optional[str]
    vonage_sms_from: Optional[str]
    music_style: str
    enable_music_generation: bool
    
    # デフォルト値の定数
    DEFAULT_GREETING_MESSAGE: str = field(
        default="お電話ありがとうございます。ただいま電話に出ることができません。発信音の後にメッセージをお残しください。",
        init=False,
        repr=False
    )
    DEFAULT_GREETING_LANGUAGE: str = field(default="ja-JP", init=False, repr=False)
    DEFAULT_GREETING_STYLE: int = field(default=0, init=False, repr=False)
    DEFAULT_MAX_RECORDING_DURATION: int = field(default=60, init=False, repr=False)
    DEFAULT_RECORDING_FORMAT: str = field(default="mp3", init=False, repr=False)
    DEFAULT_END_ON_SILENCE: int = field(default=3, init=False, repr=False)
    DEFAULT_LOG_LEVEL: str = field(default="INFO", init=False, repr=False)
    
    @classmethod
    def from_env(cls) -> 'Config':
        """
        環境変数から設定を読み込む
        
        必須の環境変数:
            - VONAGE_API_KEY: Vonage API キー
            - VONAGE_API_SECRET: Vonage API シークレット
            - VONAGE_APPLICATION_ID: Vonage アプリケーション ID
            - VONAGE_PRIVATE_KEY_PATH: Vonage 秘密鍵ファイルパス
            - WEBHOOK_BASE_URL: Webhook のベース URL
        
        オプションの環境変数:
            - GREETING_MESSAGE: 音声アナウンスメッセージ (デフォルト: 日本語グリーティング)
            - GREETING_LANGUAGE: 音声言語 (デフォルト: ja-JP)
            - GREETING_STYLE: 音声スタイル (デフォルト: 0)
            - MAX_RECORDING_DURATION: 最大録音時間（秒） (デフォルト: 60)
            - RECORDING_FORMAT: 録音フォーマット (デフォルト: mp3)
            - END_ON_SILENCE: 無音終了時間（秒） (デフォルト: 3)
            - LOG_LEVEL: ログレベル (デフォルト: INFO)
        
        Returns:
            Config: 設定オブジェクト
        
        Raises:
            ConfigurationError: 必須設定が欠落している場合
        """
        # デフォルト値
        default_greeting = "お電話ありがとうございます。ただいま電話に出ることができません。発信音の後にメッセージをお残しください。"
        
        # 必須設定の読み込み
        vonage_api_key = os.environ.get("VONAGE_API_KEY", "")
        vonage_api_secret = os.environ.get("VONAGE_API_SECRET", "")
        vonage_application_id = os.environ.get("VONAGE_APPLICATION_ID", "")
        vonage_private_key_path = os.environ.get("VONAGE_PRIVATE_KEY_PATH", "")
        webhook_base_url = os.environ.get("WEBHOOK_BASE_URL", "")
        
        # オプション設定の読み込み（デフォルト値付き）
        greeting_message = os.environ.get("GREETING_MESSAGE", default_greeting)
        greeting_language = os.environ.get("GREETING_LANGUAGE", "ja-JP")
        greeting_style = int(os.environ.get("GREETING_STYLE", "0"))
        
        max_recording_duration = int(os.environ.get("MAX_RECORDING_DURATION", "60"))
        recording_format = os.environ.get("RECORDING_FORMAT", "mp3")
        end_on_silence = int(os.environ.get("END_ON_SILENCE", "3"))
        
        log_level = os.environ.get("LOG_LEVEL", "INFO")
        
        # Webhook URLの構築
        answer_url = os.environ.get("ANSWER_URL", "")
        event_url = os.environ.get("EVENT_URL", "")
        recording_url = os.environ.get("RECORDING_URL", "")
        
        # ベースURLからWebhook URLを自動生成（個別指定がない場合）
        if webhook_base_url:
            base = webhook_base_url.rstrip("/")
            if not answer_url:
                answer_url = f"{base}/webhooks/answer"
            if not event_url:
                event_url = f"{base}/webhooks/event"
            if not recording_url:
                recording_url = f"{base}/webhooks/recording"
        
        # 音楽生成設定の読み込み
        openai_api_key = os.environ.get("OPENAI_API_KEY") or None
        udio_api_key = os.environ.get("UDIO_API_KEY") or None
        vonage_sms_from = os.environ.get("VONAGE_SMS_FROM") or None
        music_style = os.environ.get("MUSIC_STYLE", "j-pop, emotional, heartfelt, japanese")
        enable_music_generation = os.environ.get("ENABLE_MUSIC_GENERATION", "false").lower() == "true"
        
        config = cls(
            vonage_api_key=vonage_api_key,
            vonage_api_secret=vonage_api_secret,
            vonage_application_id=vonage_application_id,
            vonage_private_key_path=vonage_private_key_path,
            greeting_message=greeting_message,
            greeting_language=greeting_language,
            greeting_style=greeting_style,
            max_recording_duration=max_recording_duration,
            recording_format=recording_format,
            end_on_silence=end_on_silence,
            webhook_base_url=webhook_base_url,
            answer_url=answer_url,
            event_url=event_url,
            recording_url=recording_url,
            log_level=log_level,
            openai_api_key=openai_api_key,
            udio_api_key=udio_api_key,
            vonage_sms_from=vonage_sms_from,
            music_style=music_style,
            enable_music_generation=enable_music_generation,
        )
        
        # バリデーション実行
        config.validate()
        
        return config
    
    def validate(self) -> None:
        """
        設定の妥当性を検証
        
        必須設定が欠落している場合、明確なエラーメッセージで
        ConfigurationError を発生させます。
        
        Raises:
            ConfigurationError: 必須設定が欠落または無効な場合
        """
        missing_fields = []
        
        # Vonage API認証情報の検証 (Requirements 5.2)
        if not self.vonage_api_key:
            missing_fields.append("VONAGE_API_KEY")
        if not self.vonage_api_secret:
            missing_fields.append("VONAGE_API_SECRET")
        if not self.vonage_application_id:
            missing_fields.append("VONAGE_APPLICATION_ID")
        if not self.vonage_private_key_path:
            missing_fields.append("VONAGE_PRIVATE_KEY_PATH")
        
        # Webhook URL の検証 (Requirements 5.5)
        if not self.webhook_base_url:
            missing_fields.append("WEBHOOK_BASE_URL")
        
        # 必須設定が欠落している場合はエラー (Requirements 5.6)
        if missing_fields:
            error_message = (
                f"必須の設定が欠落しています。以下の環境変数を設定してください: "
                f"{', '.join(missing_fields)}"
            )
            raise ConfigurationError(error_message)
        
        # 数値設定の妥当性検証
        if self.max_recording_duration <= 0:
            raise ConfigurationError(
                f"MAX_RECORDING_DURATION は正の整数である必要があります: {self.max_recording_duration}"
            )
        
        if self.end_on_silence < 0:
            raise ConfigurationError(
                f"END_ON_SILENCE は0以上の整数である必要があります: {self.end_on_silence}"
            )
        
        if self.greeting_style < 0:
            raise ConfigurationError(
                f"GREETING_STYLE は0以上の整数である必要があります: {self.greeting_style}"
            )
        
        # 録音フォーマットの検証
        valid_formats = ["mp3", "wav", "ogg"]
        if self.recording_format.lower() not in valid_formats:
            raise ConfigurationError(
                f"RECORDING_FORMAT は {valid_formats} のいずれかである必要があります: {self.recording_format}"
            )
        
        # ログレベルの検証
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            raise ConfigurationError(
                f"LOG_LEVEL は {valid_log_levels} のいずれかである必要があります: {self.log_level}"
            )
