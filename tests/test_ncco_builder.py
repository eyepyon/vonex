"""
NCCO Builder テストモジュール (NCCO Builder Test Module)

TalkAction と RecordAction dataclass のユニットテストです。
"""

import pytest
from src.ncco_builder import TalkAction, RecordAction


class TestTalkAction:
    """TalkAction dataclass のテスト"""
    
    def test_talk_action_with_required_fields(self):
        """必須フィールドのみでTalkActionを作成できることを検証"""
        action = TalkAction(text="こんにちは")
        
        assert action.text == "こんにちは"
        assert action.language == "ja-JP"
        assert action.style == 0
        assert action.bargeIn is False
    
    def test_talk_action_with_all_fields(self):
        """すべてのフィールドを指定してTalkActionを作成できることを検証"""
        action = TalkAction(
            text="Hello, please leave a message.",
            language="en-US",
            style=2,
            bargeIn=True
        )
        
        assert action.text == "Hello, please leave a message."
        assert action.language == "en-US"
        assert action.style == 2
        assert action.bargeIn is True
    
    def test_talk_action_to_dict(self):
        """TalkActionのto_dict()メソッドが正しい辞書を返すことを検証"""
        action = TalkAction(
            text="お電話ありがとうございます。",
            language="ja-JP",
            style=1,
            bargeIn=False
        )
        
        result = action.to_dict()
        
        assert result == {
            "action": "talk",
            "text": "お電話ありがとうございます。",
            "language": "ja-JP",
            "style": 1,
            "bargeIn": False
        }
    
    def test_talk_action_to_dict_default_values(self):
        """デフォルト値でのto_dict()が正しい辞書を返すことを検証"""
        action = TalkAction(text="テストメッセージ")
        
        result = action.to_dict()
        
        assert result["action"] == "talk"
        assert result["text"] == "テストメッセージ"
        assert result["language"] == "ja-JP"
        assert result["style"] == 0
        assert result["bargeIn"] is False


class TestRecordAction:
    """RecordAction dataclass のテスト"""
    
    def test_record_action_with_required_fields(self):
        """必須フィールドのみでRecordActionを作成できることを検証"""
        event_url = ["https://example.com/webhooks/recording"]
        action = RecordAction(eventUrl=event_url)
        
        assert action.eventUrl == event_url
        assert action.endOnSilence == 3
        assert action.endOnKey == "#"
        assert action.beepStart is True
        assert action.timeOut == 60
        assert action.format == "mp3"
    
    def test_record_action_with_all_fields(self):
        """すべてのフィールドを指定してRecordActionを作成できることを検証"""
        event_url = ["https://example.com/webhooks/recording"]
        action = RecordAction(
            eventUrl=event_url,
            endOnSilence=5,
            endOnKey="*",
            beepStart=False,
            timeOut=120,
            format="wav"
        )
        
        assert action.eventUrl == event_url
        assert action.endOnSilence == 5
        assert action.endOnKey == "*"
        assert action.beepStart is False
        assert action.timeOut == 120
        assert action.format == "wav"
    
    def test_record_action_to_dict(self):
        """RecordActionのto_dict()メソッドが正しい辞書を返すことを検証"""
        event_url = ["https://example.com/webhooks/recording"]
        action = RecordAction(
            eventUrl=event_url,
            endOnSilence=4,
            endOnKey="#",
            beepStart=True,
            timeOut=90,
            format="mp3"
        )
        
        result = action.to_dict()
        
        assert result == {
            "action": "record",
            "eventUrl": event_url,
            "endOnSilence": 4,
            "endOnKey": "#",
            "beepStart": True,
            "timeOut": 90,
            "format": "mp3"
        }
    
    def test_record_action_to_dict_default_values(self):
        """デフォルト値でのto_dict()が正しい辞書を返すことを検証"""
        event_url = ["https://example.com/recording"]
        action = RecordAction(eventUrl=event_url)
        
        result = action.to_dict()
        
        assert result["action"] == "record"
        assert result["eventUrl"] == event_url
        assert result["endOnSilence"] == 3
        assert result["endOnKey"] == "#"
        assert result["beepStart"] is True
        assert result["timeOut"] == 60
        assert result["format"] == "mp3"
    
    def test_record_action_multiple_event_urls(self):
        """複数のeventUrlを持つRecordActionが正しく動作することを検証"""
        event_urls = [
            "https://example.com/webhooks/recording",
            "https://backup.example.com/webhooks/recording"
        ]
        action = RecordAction(eventUrl=event_urls)
        
        result = action.to_dict()
        
        assert result["eventUrl"] == event_urls
        assert len(result["eventUrl"]) == 2


from src.ncco_builder import NCCOBuilder
from src.config import Config
from unittest.mock import MagicMock


class TestNCCOBuilder:
    """NCCOBuilder クラスのテスト"""
    
    def _create_mock_config(
        self,
        greeting_message: str = "お電話ありがとうございます。",
        greeting_language: str = "ja-JP",
        greeting_style: int = 0,
        max_recording_duration: int = 60,
        recording_format: str = "mp3",
        end_on_silence: int = 3,
        recording_url: str = "https://example.com/webhooks/recording"
    ) -> MagicMock:
        """テスト用のモック設定を作成"""
        config = MagicMock(spec=Config)
        config.greeting_message = greeting_message
        config.greeting_language = greeting_language
        config.greeting_style = greeting_style
        config.max_recording_duration = max_recording_duration
        config.recording_format = recording_format
        config.end_on_silence = end_on_silence
        config.recording_url = recording_url
        return config
    
    def test_build_voicemail_ncco_returns_list(self):
        """build_voicemail_ncco()がリストを返すことを検証"""
        config = self._create_mock_config()
        builder = NCCOBuilder(config)
        
        result = builder.build_voicemail_ncco("test-uuid-123")
        
        assert isinstance(result, list)
    
    def test_build_voicemail_ncco_contains_two_actions(self):
        """build_voicemail_ncco()が2つのアクションを含むことを検証
        
        Requirements: 2.1, 2.2, 3.1, 3.2
        """
        config = self._create_mock_config()
        builder = NCCOBuilder(config)
        
        result = builder.build_voicemail_ncco("test-uuid-123")
        
        assert len(result) == 2
    
    def test_build_voicemail_ncco_first_action_is_talk(self):
        """build_voicemail_ncco()の最初のアクションがtalkであることを検証
        
        Requirements: 2.1, 2.2
        """
        config = self._create_mock_config()
        builder = NCCOBuilder(config)
        
        result = builder.build_voicemail_ncco("test-uuid-123")
        
        assert result[0]["action"] == "talk"
    
    def test_build_voicemail_ncco_second_action_is_record(self):
        """build_voicemail_ncco()の2番目のアクションがrecordであることを検証
        
        Requirements: 3.1, 3.2
        """
        config = self._create_mock_config()
        builder = NCCOBuilder(config)
        
        result = builder.build_voicemail_ncco("test-uuid-123")
        
        assert result[1]["action"] == "record"
    
    def test_build_voicemail_ncco_talk_action_uses_config_message(self):
        """talkアクションが設定のメッセージを使用することを検証
        
        Requirements: 2.3
        """
        custom_message = "カスタムメッセージです。"
        config = self._create_mock_config(greeting_message=custom_message)
        builder = NCCOBuilder(config)
        
        result = builder.build_voicemail_ncco("test-uuid-123")
        
        assert result[0]["text"] == custom_message
    
    def test_build_voicemail_ncco_talk_action_uses_config_language(self):
        """talkアクションが設定の言語を使用することを検証
        
        Requirements: 2.4
        """
        config = self._create_mock_config(greeting_language="en-US")
        builder = NCCOBuilder(config)
        
        result = builder.build_voicemail_ncco("test-uuid-123")
        
        assert result[0]["language"] == "en-US"
    
    def test_build_voicemail_ncco_talk_action_uses_config_style(self):
        """talkアクションが設定のスタイルを使用することを検証
        
        Requirements: 2.4
        """
        config = self._create_mock_config(greeting_style=2)
        builder = NCCOBuilder(config)
        
        result = builder.build_voicemail_ncco("test-uuid-123")
        
        assert result[0]["style"] == 2
    
    def test_build_voicemail_ncco_record_action_uses_config_timeout(self):
        """recordアクションが設定の最大録音時間を使用することを検証
        
        Requirements: 3.5
        """
        config = self._create_mock_config(max_recording_duration=120)
        builder = NCCOBuilder(config)
        
        result = builder.build_voicemail_ncco("test-uuid-123")
        
        assert result[1]["timeOut"] == 120
    
    def test_build_voicemail_ncco_record_action_uses_config_format(self):
        """recordアクションが設定の録音フォーマットを使用することを検証"""
        config = self._create_mock_config(recording_format="wav")
        builder = NCCOBuilder(config)
        
        result = builder.build_voicemail_ncco("test-uuid-123")
        
        assert result[1]["format"] == "wav"
    
    def test_build_voicemail_ncco_record_action_uses_config_end_on_silence(self):
        """recordアクションが設定の無音終了時間を使用することを検証"""
        config = self._create_mock_config(end_on_silence=5)
        builder = NCCOBuilder(config)
        
        result = builder.build_voicemail_ncco("test-uuid-123")
        
        assert result[1]["endOnSilence"] == 5
    
    def test_build_voicemail_ncco_record_action_uses_config_recording_url(self):
        """recordアクションが設定の録音URLを使用することを検証"""
        recording_url = "https://custom.example.com/recording"
        config = self._create_mock_config(recording_url=recording_url)
        builder = NCCOBuilder(config)
        
        result = builder.build_voicemail_ncco("test-uuid-123")
        
        assert result[1]["eventUrl"] == [recording_url]
    
    def test_build_voicemail_ncco_record_action_has_beep_start(self):
        """recordアクションがbeepStart=Trueを持つことを検証"""
        config = self._create_mock_config()
        builder = NCCOBuilder(config)
        
        result = builder.build_voicemail_ncco("test-uuid-123")
        
        assert result[1]["beepStart"] is True
    
    def test_build_voicemail_ncco_talk_action_barge_in_disabled(self):
        """talkアクションがbargeIn=Falseを持つことを検証"""
        config = self._create_mock_config()
        builder = NCCOBuilder(config)
        
        result = builder.build_voicemail_ncco("test-uuid-123")
        
        assert result[0]["bargeIn"] is False
    
    def test_build_talk_action_returns_dict(self):
        """_build_talk_action()が辞書を返すことを検証"""
        config = self._create_mock_config()
        builder = NCCOBuilder(config)
        
        result = builder._build_talk_action()
        
        assert isinstance(result, dict)
        assert result["action"] == "talk"
    
    def test_build_record_action_returns_dict(self):
        """_build_record_action()が辞書を返すことを検証"""
        config = self._create_mock_config()
        builder = NCCOBuilder(config)
        
        result = builder._build_record_action()
        
        assert isinstance(result, dict)
        assert result["action"] == "record"
    
    def test_build_voicemail_ncco_with_japanese_defaults(self):
        """日本語デフォルト設定でNCCOが正しく構築されることを検証
        
        Requirements: 2.5 (デフォルト日本語グリーティング)
        """
        default_message = "お電話ありがとうございます。ただいま電話に出ることができません。"
        config = self._create_mock_config(
            greeting_message=default_message,
            greeting_language="ja-JP",
            greeting_style=0
        )
        builder = NCCOBuilder(config)
        
        result = builder.build_voicemail_ncco("test-uuid-123")
        
        assert result[0]["text"] == default_message
        assert result[0]["language"] == "ja-JP"
        assert result[0]["style"] == 0
