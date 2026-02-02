"""
データモデルモジュール (Data Models Module)

録音データと通話ログのデータモデルを定義します。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Recording:
    """
    録音データモデル
    
    Vonage Voice APIから受信した録音情報を格納します。
    
    Attributes:
        id: 主キー (UUID)
        call_uuid: Vonage通話UUID
        conversation_uuid: Vonage会話UUID
        caller_number: 発信者電話番号
        called_number: 着信電話番号
        recording_url: 録音ファイルURL
        recording_uuid: Vonage録音UUID
        duration: 録音時間（秒）
        file_size: ファイルサイズ（バイト）
        format: 録音フォーマット (mp3, wav, ogg)
        status: ステータス (pending, completed, failed)
        local_file_path: ローカルに保存された音声ファイルのパス
        created_at: 作成日時
        updated_at: 更新日時
    """
    id: str
    call_uuid: str
    conversation_uuid: str
    caller_number: str
    called_number: str
    recording_url: str
    recording_uuid: str
    duration: int
    file_size: int
    format: str
    status: str
    local_file_path: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class CallLog:
    """
    通話ログデータモデル
    
    着信電話の通話情報を格納します。
    
    Attributes:
        id: 主キー (UUID)
        call_uuid: Vonage通話UUID
        caller_number: 発信者電話番号
        called_number: 着信電話番号
        status: 通話ステータス (started, ringing, answered, completed, failed)
        direction: 通話方向 (inbound)
        started_at: 通話開始日時
        ended_at: 通話終了日時 (通話中はNone)
        created_at: 作成日時
    """
    id: str
    call_uuid: str
    caller_number: str
    called_number: str
    status: str
    direction: str
    started_at: datetime
    ended_at: Optional[datetime]
    created_at: datetime
