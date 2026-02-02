"""
NCCO Builder モジュール (NCCO Builder Module)

Vonage Voice APIの通話フローを制御するNCCO (Nexmo Call Control Object) を構築します。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.config import Config


@dataclass
class TalkAction:
    """
    Talk NCCOアクション
    
    発信者に音声メッセージを再生するためのアクションです。
    
    Attributes:
        text: 再生するテキストメッセージ (必須)
        language: 音声の言語コード (デフォルト: ja-JP)
        style: 音声スタイル番号 (デフォルト: 0)
        bargeIn: 発信者がキー入力で中断可能かどうか (デフォルト: False)
    
    Requirements:
        - 2.1: 着信時に音声アナウンスを再生
        - 2.2: NCCOにtalkアクションとグリーティングメッセージを含める
    """
    text: str
    language: str = "ja-JP"
    style: int = 0
    bargeIn: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        NCCOアクションを辞書形式に変換
        
        Vonage APIに送信するためのJSON互換の辞書を生成します。
        
        Returns:
            Dict[str, Any]: NCCOアクションの辞書表現
        """
        return {
            "action": "talk",
            "text": self.text,
            "language": self.language,
            "style": self.style,
            "bargeIn": self.bargeIn
        }


@dataclass
class RecordAction:
    """
    Record NCCOアクション
    
    発信者の音声メッセージを録音するためのアクションです。
    
    Attributes:
        eventUrl: 録音完了時のWebhook URLリスト (必須)
        endOnSilence: 無音で録音を終了するまでの秒数 (デフォルト: 3)
        endOnKey: 録音を終了するキー (デフォルト: #)
        beepStart: 録音開始時にビープ音を鳴らすかどうか (デフォルト: True)
        timeOut: 最大録音時間（秒） (デフォルト: 60)
        format: 録音フォーマット (デフォルト: mp3)
    
    Requirements:
        - 3.1: 音声アナウンス終了後に録音を開始
        - 3.2: NCCOに適切な設定のrecordアクションを含める
    """
    eventUrl: List[str]
    endOnSilence: int = 3
    endOnKey: str = "#"
    beepStart: bool = True
    timeOut: int = 60
    format: str = "mp3"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        NCCOアクションを辞書形式に変換
        
        Vonage APIに送信するためのJSON互換の辞書を生成します。
        
        Returns:
            Dict[str, Any]: NCCOアクションの辞書表現
        """
        return {
            "action": "record",
            "eventUrl": self.eventUrl,
            "endOnSilence": self.endOnSilence,
            "endOnKey": self.endOnKey,
            "beepStart": self.beepStart,
            "timeOut": self.timeOut,
            "format": self.format
        }


class NCCOBuilder:
    """
    NCCOを構築するビルダークラス
    
    Vonage Voice APIの通話フローを制御するNCCOを構築します。
    設定に基づいてTalkアクションとRecordアクションを生成し、
    ボイスメール用のNCCOを作成します。
    
    Attributes:
        config: アプリケーション設定オブジェクト
    
    Requirements:
        - 2.1: 着信時に音声アナウンスを再生
        - 2.2: NCCOにtalkアクションとグリーティングメッセージを含める
        - 2.3: 設定可能なメッセージテキストを使用
        - 2.4: 設定可能な音声スタイルと言語を使用
        - 3.1: 音声アナウンス終了後に録音を開始
        - 3.2: NCCOに適切な設定のrecordアクションを含める
        - 3.5: 設定可能な最大録音時間を適用
    """
    
    def __init__(self, config: 'Config'):
        """
        NCCOBuilderを初期化
        
        Args:
            config: アプリケーション設定オブジェクト
        """
        self.config = config
    
    def build_voicemail_ncco(self, call_uuid: str) -> List[Dict[str, Any]]:
        """
        ボイスメール用NCCOを構築
        
        音声アナウンス（Talk）と録音（Record）のアクションを含む
        NCCOを生成します。Talkアクションが先に実行され、
        その後Recordアクションが実行されます。
        
        Args:
            call_uuid: 通話UUID（ログ記録やトラッキング用）
        
        Returns:
            NCCOアクションのリスト（Talk + Record）
        
        Requirements:
            - 2.1: 着信時に音声アナウンスを再生
            - 2.2: NCCOにtalkアクションとグリーティングメッセージを含める
            - 3.1: 音声アナウンス終了後に録音を開始
            - 3.2: NCCOに適切な設定のrecordアクションを含める
        """
        ncco = []
        
        # Talk アクションを追加（音声アナウンス）
        talk_action = self._build_talk_action()
        ncco.append(talk_action)
        
        # Record アクションを追加（録音）
        record_action = self._build_record_action()
        ncco.append(record_action)
        
        return ncco
    
    def _build_talk_action(self) -> Dict[str, Any]:
        """
        Talk アクションを構築
        
        設定に基づいて音声アナウンス用のTalkアクションを生成します。
        
        Returns:
            Talkアクションの辞書表現
        
        Requirements:
            - 2.2: NCCOにtalkアクションとグリーティングメッセージを含める
            - 2.3: 設定可能なメッセージテキストを使用
            - 2.4: 設定可能な音声スタイルと言語を使用
        """
        talk = TalkAction(
            text=self.config.greeting_message,
            language=self.config.greeting_language,
            style=self.config.greeting_style,
            bargeIn=False  # 音声アナウンス中は中断不可
        )
        return talk.to_dict()
    
    def _build_record_action(self) -> Dict[str, Any]:
        """
        Record アクションを構築
        
        設定に基づいて録音用のRecordアクションを生成します。
        
        Returns:
            Recordアクションの辞書表現
        
        Requirements:
            - 3.2: NCCOに適切な設定のrecordアクションを含める
            - 3.5: 設定可能な最大録音時間を適用
        """
        record = RecordAction(
            eventUrl=[self.config.recording_url],
            endOnSilence=self.config.end_on_silence,
            endOnKey="#",
            beepStart=True,
            timeOut=self.config.max_recording_duration,
            format=self.config.recording_format
        )
        return record.to_dict()
