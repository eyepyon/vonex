"""
録音マネージャーモジュール (Recording Manager Module)

録音データの管理を担当するクラスを提供します。
音声ファイルのダウンロードと保存機能も提供します。
"""

import os
import requests
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
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
        local_file_path: ローカルに保存されたファイルパス（オプション）
    """
    id: str
    call_uuid: str
    caller_number: str
    recording_url: str
    duration: int
    timestamp: datetime
    status: str
    local_file_path: Optional[str] = None


class RecordingManager:
    """
    録音データを管理するクラス
    
    録音メタデータの保存、取得、一覧表示を担当します。
    Storage レイヤーを使用してデータの永続化を行います。
    音声ファイルのダウンロードと保存も行います。
    
    Validates:
        - Requirements 3.4: Recording_URL受信時に録音メタデータを保存
        - Requirements 4.1: 録音完了時にメタデータをストレージに永続化
        - Requirements 4.4: 通話UUIDで録音メタデータを取得する方法を提供
        - Requirements 4.5: 日付フィルタリング付きで全録音を一覧表示する方法を提供
    """
    
    # 録音ファイル保存ディレクトリ
    DEFAULT_RECORDINGS_DIR = "recordings"
    
    def __init__(
        self,
        storage: Storage,
        recordings_dir: Optional[str] = None,
        vonage_api_key: Optional[str] = None,
        vonage_api_secret: Optional[str] = None
    ):
        """
        RecordingManagerを初期化
        
        Args:
            storage: データ永続化に使用するStorageインスタンス
            recordings_dir: 録音ファイル保存ディレクトリ（オプション）
            vonage_api_key: Vonage APIキー（ダウンロード認証用）
            vonage_api_secret: Vonage APIシークレット（ダウンロード認証用）
        """
        self.storage = storage
        self.recordings_dir = recordings_dir or self.DEFAULT_RECORDINGS_DIR
        self.vonage_api_key = vonage_api_key
        self.vonage_api_secret = vonage_api_secret
        
        # 録音ディレクトリを作成
        self._ensure_recordings_dir()
    
    def _ensure_recordings_dir(self) -> None:
        """録音ディレクトリが存在することを確認し、なければ作成"""
        Path(self.recordings_dir).mkdir(parents=True, exist_ok=True)
    
    def download_recording(
        self,
        recording_url: str,
        recording_id: str,
        format: str = "mp3"
    ) -> Optional[str]:
        """
        Vonageから録音ファイルをダウンロードしてローカルに保存
        
        Args:
            recording_url: Vonageの録音ファイルURL
            recording_id: 録音ID（ファイル名に使用）
            format: 録音フォーマット
        
        Returns:
            保存されたファイルのパス、失敗した場合はNone
        """
        if not recording_url:
            return None
        
        try:
            # ファイル名を生成
            filename = f"{recording_id}.{format}"
            file_path = os.path.join(self.recordings_dir, filename)
            
            # Vonage APIで認証してダウンロード
            # Vonageの録音URLはJWT認証が必要
            headers = {}
            auth = None
            
            if self.vonage_api_key and self.vonage_api_secret:
                # Basic認証を使用
                auth = (self.vonage_api_key, self.vonage_api_secret)
            
            response = requests.get(
                recording_url,
                auth=auth,
                headers=headers,
                timeout=60,
                stream=True
            )
            response.raise_for_status()
            
            # ファイルに保存
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return file_path
            
        except requests.RequestException as e:
            # ダウンロード失敗時はログを出力してNoneを返す
            print(f"録音ファイルのダウンロードに失敗しました: {e}")
            return None
        except IOError as e:
            print(f"録音ファイルの保存に失敗しました: {e}")
            return None
    
    def save_recording(
        self,
        metadata: RecordingMetadata,
        conversation_uuid: Optional[str] = None,
        called_number: Optional[str] = None,
        recording_uuid: Optional[str] = None,
        file_size: Optional[int] = None,
        format: str = "mp3",
        download_file: bool = True
    ) -> None:
        """
        録音メタデータを保存
        
        RecordingMetadataを受け取り、完全なRecordingモデルに変換して
        ストレージに永続化します。オプションで音声ファイルもダウンロードします。
        
        Args:
            metadata: 録音メタデータ
            conversation_uuid: Vonage会話UUID（オプション）
            called_number: 着信電話番号（オプション）
            recording_uuid: Vonage録音UUID（オプション）
            file_size: ファイルサイズ（バイト）（オプション）
            format: 録音フォーマット（デフォルト: mp3）
            download_file: 音声ファイルをダウンロードするか（デフォルト: True）
        
        Raises:
            StorageError: 保存に失敗した場合
        
        Validates: Requirements 3.4, 4.1
        """
        now = datetime.now()
        
        # 音声ファイルをダウンロード
        local_file_path = None
        if download_file and metadata.recording_url:
            local_file_path = self.download_recording(
                recording_url=metadata.recording_url,
                recording_id=metadata.id,
                format=format
            )
        
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
            updated_at=now,
            local_file_path=local_file_path
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
