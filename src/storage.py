"""
ストレージモジュール (Storage Module)

データベース操作を抽象化するストレージレイヤーを提供します。
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from .models import CallLog, Recording


class Storage(ABC):
    """
    ストレージの抽象基底クラス
    
    録音データと通話ログの永続化を担当する抽象インターフェースを定義します。
    具体的な実装（SQLite、PostgreSQL等）はこのクラスを継承して実装します。
    
    Validates:
        - Requirements 4.1: 録音完了時にメタデータをストレージに永続化
        - Requirements 4.4: 通話UUIDで録音メタデータを取得する方法を提供
        - Requirements 4.5: 日付フィルタリング付きで全録音を一覧表示する方法を提供
    """
    
    @abstractmethod
    def save_recording(self, recording: Recording) -> None:
        """
        録音メタデータを保存
        
        録音完了時に呼び出され、録音のメタデータをストレージに永続化します。
        
        Args:
            recording: 保存する録音データモデル
        
        Raises:
            StorageError: 保存に失敗した場合
        
        Validates: Requirements 4.1
        """
        pass
    
    @abstractmethod
    def get_recording(self, call_uuid: str) -> Optional[Recording]:
        """
        通話UUIDで録音を取得
        
        指定された通話UUIDに対応する録音メタデータを取得します。
        
        Args:
            call_uuid: Vonage通話UUID
        
        Returns:
            録音データモデル、見つからない場合はNone
        
        Raises:
            StorageError: 取得に失敗した場合
        
        Validates: Requirements 4.4
        """
        pass
    
    @abstractmethod
    def list_recordings(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Recording]:
        """
        録音一覧を取得
        
        オプションの日付範囲フィルタを使用して録音の一覧を取得します。
        フィルタが指定されない場合は全ての録音を返します。
        
        Args:
            start_date: 開始日時（この日時以降の録音を取得）
            end_date: 終了日時（この日時以前の録音を取得）
        
        Returns:
            録音データモデルのリスト
        
        Raises:
            StorageError: 取得に失敗した場合
        
        Validates: Requirements 4.5
        """
        pass
    
    @abstractmethod
    def save_call_log(self, call_log: CallLog) -> None:
        """
        通話ログを保存
        
        通話の開始、終了、ステータス変更時に呼び出され、
        通話ログをストレージに永続化します。
        
        Args:
            call_log: 保存する通話ログデータモデル
        
        Raises:
            StorageError: 保存に失敗した場合
        """
        pass
    
    @abstractmethod
    def update_call_log_status(
        self,
        call_uuid: str,
        status: str,
        ended_at: Optional[datetime] = None
    ) -> bool:
        """
        通話ログのステータスを更新
        
        通話イベント受信時に呼び出され、通話ログのステータスを更新します。
        
        Args:
            call_uuid: Vonage通話UUID
            status: 新しいステータス
            ended_at: 通話終了日時（オプション）
        
        Returns:
            更新が成功した場合はTrue、通話ログが見つからない場合はFalse
        
        Raises:
            StorageError: 更新に失敗した場合
        
        Validates: Requirements 3.6
        """
        pass
    
    @abstractmethod
    def get_call_log(self, call_uuid: str) -> Optional[CallLog]:
        """
        通話UUIDで通話ログを取得
        
        指定された通話UUIDに対応する通話ログを取得します。
        
        Args:
            call_uuid: Vonage通話UUID
        
        Returns:
            通話ログデータモデル、見つからない場合はNone
        
        Raises:
            StorageError: 取得に失敗した場合
        """
        pass


import sqlite3
from contextlib import contextmanager
from typing import Generator


class StorageError(Exception):
    """
    ストレージエラー
    
    データベース操作中に発生したエラーを表す例外クラスです。
    """
    pass


class SQLiteStorage(Storage):
    """
    SQLite実装
    
    SQLiteデータベースを使用したストレージ実装です。
    開発環境やシンプルなデプロイメントに適しています。
    
    Validates:
        - Requirements 4.1: 録音完了時にメタデータをストレージに永続化
        - Requirements 4.4: 通話UUIDで録音メタデータを取得する方法を提供
        - Requirements 4.5: 日付フィルタリング付きで全録音を一覧表示する方法を提供
    """
    
    def __init__(self, db_path: str = "voice_recorder.db"):
        """
        SQLiteStorageを初期化
        
        Args:
            db_path: SQLiteデータベースファイルのパス
        """
        self.db_path = db_path
        self._create_tables()
    
    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        データベース接続のコンテキストマネージャー
        
        Yields:
            SQLite接続オブジェクト
        
        Raises:
            StorageError: 接続に失敗した場合
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            raise StorageError(f"Database connection error: {e}") from e
        finally:
            if conn:
                conn.close()
    
    def _create_tables(self) -> None:
        """
        データベーステーブルを作成
        
        Recording と CallLog テーブルが存在しない場合に作成します。
        
        Raises:
            StorageError: テーブル作成に失敗した場合
        """
        create_recording_table = """
        CREATE TABLE IF NOT EXISTS recordings (
            id VARCHAR(36) PRIMARY KEY,
            call_uuid VARCHAR(36) NOT NULL,
            conversation_uuid VARCHAR(36) NOT NULL,
            caller_number VARCHAR(20) NOT NULL,
            called_number VARCHAR(20) NOT NULL,
            recording_url TEXT NOT NULL,
            recording_uuid VARCHAR(36) NOT NULL,
            duration INTEGER NOT NULL,
            file_size INTEGER NOT NULL,
            format VARCHAR(10) NOT NULL,
            status VARCHAR(20) NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
        """
        
        create_call_log_table = """
        CREATE TABLE IF NOT EXISTS call_logs (
            id VARCHAR(36) PRIMARY KEY,
            call_uuid VARCHAR(36) NOT NULL,
            caller_number VARCHAR(20) NOT NULL,
            called_number VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL,
            direction VARCHAR(10) NOT NULL,
            started_at TIMESTAMP NOT NULL,
            ended_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL
        )
        """
        
        # Create indexes for common queries
        create_recording_call_uuid_index = """
        CREATE INDEX IF NOT EXISTS idx_recordings_call_uuid ON recordings(call_uuid)
        """
        
        create_recording_created_at_index = """
        CREATE INDEX IF NOT EXISTS idx_recordings_created_at ON recordings(created_at)
        """
        
        create_call_log_call_uuid_index = """
        CREATE INDEX IF NOT EXISTS idx_call_logs_call_uuid ON call_logs(call_uuid)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(create_recording_table)
                cursor.execute(create_call_log_table)
                cursor.execute(create_recording_call_uuid_index)
                cursor.execute(create_recording_created_at_index)
                cursor.execute(create_call_log_call_uuid_index)
                conn.commit()
        except sqlite3.Error as e:
            raise StorageError(f"Failed to create tables: {e}") from e
    
    def save_recording(self, recording: Recording) -> None:
        """
        録音メタデータを保存
        
        録音完了時に呼び出され、録音のメタデータをSQLiteデータベースに永続化します。
        同じIDの録音が存在する場合は更新します。
        
        Args:
            recording: 保存する録音データモデル
        
        Raises:
            StorageError: 保存に失敗した場合
        
        Validates: Requirements 4.1
        """
        sql = """
        INSERT OR REPLACE INTO recordings (
            id, call_uuid, conversation_uuid, caller_number, called_number,
            recording_url, recording_uuid, duration, file_size, format,
            status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (
                    recording.id,
                    recording.call_uuid,
                    recording.conversation_uuid,
                    recording.caller_number,
                    recording.called_number,
                    recording.recording_url,
                    recording.recording_uuid,
                    recording.duration,
                    recording.file_size,
                    recording.format,
                    recording.status,
                    recording.created_at.isoformat(),
                    recording.updated_at.isoformat()
                ))
                conn.commit()
        except sqlite3.Error as e:
            raise StorageError(f"Failed to save recording: {e}") from e
    
    def get_recording(self, call_uuid: str) -> Optional[Recording]:
        """
        通話UUIDで録音を取得
        
        指定された通話UUIDに対応する録音メタデータを取得します。
        
        Args:
            call_uuid: Vonage通話UUID
        
        Returns:
            録音データモデル、見つからない場合はNone
        
        Raises:
            StorageError: 取得に失敗した場合
        
        Validates: Requirements 4.4
        """
        sql = """
        SELECT id, call_uuid, conversation_uuid, caller_number, called_number,
               recording_url, recording_uuid, duration, file_size, format,
               status, created_at, updated_at
        FROM recordings
        WHERE call_uuid = ?
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (call_uuid,))
                row = cursor.fetchone()
                
                if row is None:
                    return None
                
                return self._row_to_recording(row)
        except sqlite3.Error as e:
            raise StorageError(f"Failed to get recording: {e}") from e
    
    def list_recordings(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Recording]:
        """
        録音一覧を取得
        
        オプションの日付範囲フィルタを使用して録音の一覧を取得します。
        フィルタが指定されない場合は全ての録音を返します。
        
        Args:
            start_date: 開始日時（この日時以降の録音を取得）
            end_date: 終了日時（この日時以前の録音を取得）
        
        Returns:
            録音データモデルのリスト
        
        Raises:
            StorageError: 取得に失敗した場合
        
        Validates: Requirements 4.5
        """
        sql = """
        SELECT id, call_uuid, conversation_uuid, caller_number, called_number,
               recording_url, recording_uuid, duration, file_size, format,
               status, created_at, updated_at
        FROM recordings
        """
        
        conditions = []
        params: List[str] = []
        
        if start_date is not None:
            conditions.append("created_at >= ?")
            params.append(start_date.isoformat())
        
        if end_date is not None:
            conditions.append("created_at <= ?")
            params.append(end_date.isoformat())
        
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        sql += " ORDER BY created_at DESC"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                return [self._row_to_recording(row) for row in rows]
        except sqlite3.Error as e:
            raise StorageError(f"Failed to list recordings: {e}") from e
    
    def save_call_log(self, call_log: CallLog) -> None:
        """
        通話ログを保存
        
        通話の開始、終了、ステータス変更時に呼び出され、
        通話ログをSQLiteデータベースに永続化します。
        同じIDの通話ログが存在する場合は更新します。
        
        Args:
            call_log: 保存する通話ログデータモデル
        
        Raises:
            StorageError: 保存に失敗した場合
        """
        sql = """
        INSERT OR REPLACE INTO call_logs (
            id, call_uuid, caller_number, called_number, status,
            direction, started_at, ended_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (
                    call_log.id,
                    call_log.call_uuid,
                    call_log.caller_number,
                    call_log.called_number,
                    call_log.status,
                    call_log.direction,
                    call_log.started_at.isoformat(),
                    call_log.ended_at.isoformat() if call_log.ended_at else None,
                    call_log.created_at.isoformat()
                ))
                conn.commit()
        except sqlite3.Error as e:
            raise StorageError(f"Failed to save call log: {e}") from e
    
    def _row_to_recording(self, row: sqlite3.Row) -> Recording:
        """
        SQLite行をRecordingオブジェクトに変換
        
        Args:
            row: SQLite行オブジェクト
        
        Returns:
            Recording データモデル
        """
        return Recording(
            id=row["id"],
            call_uuid=row["call_uuid"],
            conversation_uuid=row["conversation_uuid"],
            caller_number=row["caller_number"],
            called_number=row["called_number"],
            recording_url=row["recording_url"],
            recording_uuid=row["recording_uuid"],
            duration=row["duration"],
            file_size=row["file_size"],
            format=row["format"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )
    
    def get_call_log(self, call_uuid: str) -> Optional[CallLog]:
        """
        通話UUIDで通話ログを取得
        
        指定された通話UUIDに対応する通話ログを取得します。
        
        Args:
            call_uuid: Vonage通話UUID
        
        Returns:
            通話ログデータモデル、見つからない場合はNone
        
        Raises:
            StorageError: 取得に失敗した場合
        """
        sql = """
        SELECT id, call_uuid, caller_number, called_number, status,
               direction, started_at, ended_at, created_at
        FROM call_logs
        WHERE call_uuid = ?
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (call_uuid,))
                row = cursor.fetchone()
                
                if row is None:
                    return None
                
                return self._row_to_call_log(row)
        except sqlite3.Error as e:
            raise StorageError(f"Failed to get call log: {e}") from e
    
    def _row_to_call_log(self, row: sqlite3.Row) -> CallLog:
        """
        SQLite行をCallLogオブジェクトに変換
        
        Args:
            row: SQLite行オブジェクト
        
        Returns:
            CallLog データモデル
        """
        return CallLog(
            id=row["id"],
            call_uuid=row["call_uuid"],
            caller_number=row["caller_number"],
            called_number=row["called_number"],
            status=row["status"],
            direction=row["direction"],
            started_at=datetime.fromisoformat(row["started_at"]),
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"])
        )
    
    def update_call_log_status(
        self,
        call_uuid: str,
        status: str,
        ended_at: Optional[datetime] = None
    ) -> bool:
        """
        通話ログのステータスを更新
        
        通話イベント受信時に呼び出され、通話ログのステータスを更新します。
        
        Args:
            call_uuid: Vonage通話UUID
            status: 新しいステータス
            ended_at: 通話終了日時（オプション）
        
        Returns:
            更新が成功した場合はTrue、通話ログが見つからない場合はFalse
        
        Raises:
            StorageError: 更新に失敗した場合
        
        Validates: Requirements 3.6
        """
        # まず通話ログが存在するか確認
        existing_log = self.get_call_log(call_uuid)
        if existing_log is None:
            return False
        
        sql = """
        UPDATE call_logs
        SET status = ?, ended_at = ?
        WHERE call_uuid = ?
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (
                    status,
                    ended_at.isoformat() if ended_at else None,
                    call_uuid
                ))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            raise StorageError(f"Failed to update call log status: {e}") from e
