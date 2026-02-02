"""
録音マネージャーモジュール (Recording Manager Module)

録音データの管理を担当するクラスを提供します。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import uuid

from .models import Recording
from .storage import Storage


@dataclass
class RecordingMetadata:
    """
    録音メタデータ
    
    録音の基本情報を格納する簡易データクラスです。
    Webhookから受信したデータを一時的に保持し、
    Recording モデルに変換するために使用します。
    
    Attributes:
        id: 録音ID (UUID)
        call_uuid: Vonage通話UUID
        caller_number: 発信者電話番号
        recording_url: 録音ファイルURL
        duration: 録音時間（秒）
        timestamp: 録音日時
        status: ステータス
    """
    id: str
    call_uuid: str
    caller_number: str
    recording_url: str
    duration: int
    timestamp: datetime
    status: str


class RecordingManager:
    """
    録音データを管理するクラス
    
    録音メタデータの保存、取得、一覧表示を担当します。
    Storage レイヤーを使用してデータの永続化を行います。
    
    Validates:
        - Requirements 3.4: Recording_URL受信時に録音メタデータを保存
        - Requirements 4.1: 録音完了時にメタデータをストレージに永続化
        - Requirements 4.4: 通話UUIDで録音メタデータを取得する方法を提供
        - Requirements 4.5: 日付フィルタリング付きで全録音を一覧表示する方法を提供
    """
    
    def __init__(self, storage: Storage):
        """
        RecordingManagerを初期化
        
        Args:
            storage: データ永続化に使用するStorageインスタンス
        """
        self.storage = storage
    
    def save_recording(
        self,
        metadata: RecordingMetadata,
        conversation_uuid: Optional[str] = None,
        called_number: Optional[str] = None,
        recording_uuid: Optional[str] = None,
        file_size: Optional[int] = None,
        format: str = "mp3"
    ) -> None:
        """
        録音メタデータを保存
        
        RecordingMetadataを受け取り、完全なRecordingモデルに変換して
        ストレージに永続化します。
        
        Args:
            metadata: 録音メタデータ
            conversation_uuid: Vonage会話UUID（オプション）
            called_number: 着信電話番号（オプション）
            recording_uuid: Vonage録音UUID（オプション）
            file_size: ファイルサイズ（バイト）（オプション）
            format: 録音フォーマット（デフォルト: mp3）
        
        Raises:
            StorageError: 保存に失敗した場合
        
        Validates: Requirements 3.4, 4.1
        """
        now = datetime.now()
        
        recording = Recording(
            id=metadata.id,
            call_uuid=metadata.call_uuid,
            conversation_uuid=conversation_uuid or str(uuid.uuid4()),
            caller_number=metadata.caller_number,
            called_number=called_number or "",
            recording_url=metadata.recording_url,
            recording_uuid=recording_uuid or str(uuid.uuid4()),
            duration=metadata.duration,
            file_size=file_size or 0,
            format=format,
            status=metadata.status,
            created_at=metadata.timestamp,
            updated_at=now
        )
        
        self.storage.save_recording(recording)
    
    def get_recording(self, call_uuid: str) -> Optional[RecordingMetadata]:
        """
        通話UUIDで録音を取得
        
        指定された通話UUIDに対応する録音メタデータを取得します。
        
        Args:
            call_uuid: Vonage通話UUID
        
        Returns:
            録音メタデータ、見つからない場合はNone
        
        Raises:
            StorageError: 取得に失敗した場合
        
        Validates: Requirements 4.4
        """
        recording = self.storage.get_recording(call_uuid)
        
        if recording is None:
            return None
        
        return self._recording_to_metadata(recording)
    
    def list_recordings(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[RecordingMetadata]:
        """
        録音一覧を取得
        
        オプションの日付範囲フィルタを使用して録音の一覧を取得します。
        フィルタが指定されない場合は全ての録音を返します。
        
        Args:
            start_date: 開始日時（この日時以降の録音を取得）
            end_date: 終了日時（この日時以前の録音を取得）
        
        Returns:
            録音メタデータのリスト
        
        Raises:
            StorageError: 取得に失敗した場合
        
        Validates: Requirements 4.5
        """
        recordings = self.storage.list_recordings(
            start_date=start_date,
            end_date=end_date
        )
        
        return [self._recording_to_metadata(r) for r in recordings]
    
    def _recording_to_metadata(self, recording: Recording) -> RecordingMetadata:
        """
        RecordingモデルをRecordingMetadataに変換
        
        Args:
            recording: Recording データモデル
        
        Returns:
            RecordingMetadata
        """
        return RecordingMetadata(
            id=recording.id,
            call_uuid=recording.call_uuid,
            caller_number=recording.caller_number,
            recording_url=recording.recording_url,
            duration=recording.duration,
            timestamp=recording.created_at,
            status=recording.status
        )
