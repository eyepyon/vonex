"""
SQLiteStorage クラスのユニットテスト

Requirements 4.1, 4.4, 4.5 の検証
"""

import os
import tempfile
from datetime import datetime, timedelta

import pytest

from src.models import CallLog, Recording
from src.storage import SQLiteStorage, StorageError


class TestSQLiteStorageInit:
    """SQLiteStorage 初期化のテスト"""
    
    def test_creates_database_file(self):
        """
        正常系: データベースファイルが作成される
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = SQLiteStorage(db_path)
            
            assert os.path.exists(db_path)
    
    def test_creates_tables_on_init(self):
        """
        正常系: 初期化時にテーブルが作成される
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage = SQLiteStorage(db_path)
            
            # テーブルが存在することを確認
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # recordings テーブルの確認
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='recordings'")
            assert cursor.fetchone() is not None
            
            # call_logs テーブルの確認
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='call_logs'")
            assert cursor.fetchone() is not None
            
            conn.close()


class TestSQLiteStorageSaveRecording:
    """SQLiteStorage.save_recording() のテスト"""
    
    @pytest.fixture
    def storage(self):
        """テスト用のSQLiteStorageインスタンス"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            yield SQLiteStorage(db_path)
    
    @pytest.fixture
    def sample_recording(self):
        """サンプル録音データ"""
        now = datetime.now()
        return Recording(
            id="rec-123",
            call_uuid="call-456",
            conversation_uuid="conv-789",
            caller_number="+81901234567",
            called_number="+81312345678",
            recording_url="https://api.nexmo.com/v1/files/abc123",
            recording_uuid="recording-uuid-123",
            duration=30,
            file_size=50000,
            format="mp3",
            status="completed",
            created_at=now,
            updated_at=now
        )
    
    def test_save_recording_success(self, storage, sample_recording):
        """
        正常系: 録音メタデータが正常に保存される
        Requirements: 4.1
        """
        storage.save_recording(sample_recording)
        
        # 保存されたことを確認
        retrieved = storage.get_recording(sample_recording.call_uuid)
        assert retrieved is not None
        assert retrieved.id == sample_recording.id
        assert retrieved.call_uuid == sample_recording.call_uuid
    
    def test_save_recording_updates_existing(self, storage, sample_recording):
        """
        正常系: 同じIDの録音が存在する場合、更新される
        """
        storage.save_recording(sample_recording)
        
        # 更新
        updated_recording = Recording(
            id=sample_recording.id,
            call_uuid=sample_recording.call_uuid,
            conversation_uuid=sample_recording.conversation_uuid,
            caller_number=sample_recording.caller_number,
            called_number=sample_recording.called_number,
            recording_url=sample_recording.recording_url,
            recording_uuid=sample_recording.recording_uuid,
            duration=60,  # 変更
            file_size=100000,  # 変更
            format=sample_recording.format,
            status="completed",
            created_at=sample_recording.created_at,
            updated_at=datetime.now()
        )
        storage.save_recording(updated_recording)
        
        # 更新されたことを確認
        retrieved = storage.get_recording(sample_recording.call_uuid)
        assert retrieved.duration == 60
        assert retrieved.file_size == 100000


class TestSQLiteStorageGetRecording:
    """SQLiteStorage.get_recording() のテスト"""
    
    @pytest.fixture
    def storage(self):
        """テスト用のSQLiteStorageインスタンス"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            yield SQLiteStorage(db_path)
    
    @pytest.fixture
    def sample_recording(self):
        """サンプル録音データ"""
        now = datetime.now()
        return Recording(
            id="rec-123",
            call_uuid="call-456",
            conversation_uuid="conv-789",
            caller_number="+81901234567",
            called_number="+81312345678",
            recording_url="https://api.nexmo.com/v1/files/abc123",
            recording_uuid="recording-uuid-123",
            duration=30,
            file_size=50000,
            format="mp3",
            status="completed",
            created_at=now,
            updated_at=now
        )
    
    def test_get_recording_found(self, storage, sample_recording):
        """
        正常系: 存在する録音が取得できる
        Requirements: 4.4
        """
        storage.save_recording(sample_recording)
        
        retrieved = storage.get_recording(sample_recording.call_uuid)
        
        assert retrieved is not None
        assert retrieved.id == sample_recording.id
        assert retrieved.call_uuid == sample_recording.call_uuid
        assert retrieved.conversation_uuid == sample_recording.conversation_uuid
        assert retrieved.caller_number == sample_recording.caller_number
        assert retrieved.called_number == sample_recording.called_number
        assert retrieved.recording_url == sample_recording.recording_url
        assert retrieved.recording_uuid == sample_recording.recording_uuid
        assert retrieved.duration == sample_recording.duration
        assert retrieved.file_size == sample_recording.file_size
        assert retrieved.format == sample_recording.format
        assert retrieved.status == sample_recording.status
    
    def test_get_recording_not_found(self, storage):
        """
        エッジケース: 存在しない録音の場合、Noneが返される
        Requirements: 4.4
        """
        retrieved = storage.get_recording("non-existent-uuid")
        
        assert retrieved is None


class TestSQLiteStorageListRecordings:
    """SQLiteStorage.list_recordings() のテスト"""
    
    @pytest.fixture
    def storage(self):
        """テスト用のSQLiteStorageインスタンス"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            yield SQLiteStorage(db_path)
    
    def _create_recording(self, id: str, call_uuid: str, created_at: datetime) -> Recording:
        """テスト用録音データを作成"""
        return Recording(
            id=id,
            call_uuid=call_uuid,
            conversation_uuid=f"conv-{id}",
            caller_number="+81901234567",
            called_number="+81312345678",
            recording_url=f"https://api.nexmo.com/v1/files/{id}",
            recording_uuid=f"rec-uuid-{id}",
            duration=30,
            file_size=50000,
            format="mp3",
            status="completed",
            created_at=created_at,
            updated_at=created_at
        )
    
    def test_list_recordings_empty(self, storage):
        """
        エッジケース: 録音がない場合、空のリストが返される
        Requirements: 4.5
        """
        recordings = storage.list_recordings()
        
        assert recordings == []
    
    def test_list_recordings_all(self, storage):
        """
        正常系: フィルタなしで全ての録音が返される
        Requirements: 4.5
        """
        now = datetime.now()
        rec1 = self._create_recording("rec-1", "call-1", now - timedelta(days=2))
        rec2 = self._create_recording("rec-2", "call-2", now - timedelta(days=1))
        rec3 = self._create_recording("rec-3", "call-3", now)
        
        storage.save_recording(rec1)
        storage.save_recording(rec2)
        storage.save_recording(rec3)
        
        recordings = storage.list_recordings()
        
        assert len(recordings) == 3
        # 新しい順にソートされている
        assert recordings[0].id == "rec-3"
        assert recordings[1].id == "rec-2"
        assert recordings[2].id == "rec-1"
    
    def test_list_recordings_with_start_date(self, storage):
        """
        正常系: start_dateフィルタで指定日時以降の録音が返される
        Requirements: 4.5
        """
        now = datetime.now()
        rec1 = self._create_recording("rec-1", "call-1", now - timedelta(days=3))
        rec2 = self._create_recording("rec-2", "call-2", now - timedelta(days=1))
        rec3 = self._create_recording("rec-3", "call-3", now)
        
        storage.save_recording(rec1)
        storage.save_recording(rec2)
        storage.save_recording(rec3)
        
        recordings = storage.list_recordings(start_date=now - timedelta(days=2))
        
        assert len(recordings) == 2
        assert recordings[0].id == "rec-3"
        assert recordings[1].id == "rec-2"
    
    def test_list_recordings_with_end_date(self, storage):
        """
        正常系: end_dateフィルタで指定日時以前の録音が返される
        Requirements: 4.5
        """
        now = datetime.now()
        rec1 = self._create_recording("rec-1", "call-1", now - timedelta(days=3))
        rec2 = self._create_recording("rec-2", "call-2", now - timedelta(days=1))
        rec3 = self._create_recording("rec-3", "call-3", now)
        
        storage.save_recording(rec1)
        storage.save_recording(rec2)
        storage.save_recording(rec3)
        
        recordings = storage.list_recordings(end_date=now - timedelta(days=2))
        
        assert len(recordings) == 1
        assert recordings[0].id == "rec-1"
    
    def test_list_recordings_with_date_range(self, storage):
        """
        正常系: start_dateとend_dateの両方で日付範囲フィルタが適用される
        Requirements: 4.5
        """
        now = datetime.now()
        rec1 = self._create_recording("rec-1", "call-1", now - timedelta(days=5))
        rec2 = self._create_recording("rec-2", "call-2", now - timedelta(days=3))
        rec3 = self._create_recording("rec-3", "call-3", now - timedelta(days=1))
        rec4 = self._create_recording("rec-4", "call-4", now)
        
        storage.save_recording(rec1)
        storage.save_recording(rec2)
        storage.save_recording(rec3)
        storage.save_recording(rec4)
        
        recordings = storage.list_recordings(
            start_date=now - timedelta(days=4),
            end_date=now - timedelta(hours=12)
        )
        
        assert len(recordings) == 2
        assert recordings[0].id == "rec-3"
        assert recordings[1].id == "rec-2"


class TestSQLiteStorageSaveCallLog:
    """SQLiteStorage.save_call_log() のテスト"""
    
    @pytest.fixture
    def storage(self):
        """テスト用のSQLiteStorageインスタンス"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            yield SQLiteStorage(db_path)
    
    @pytest.fixture
    def sample_call_log(self):
        """サンプル通話ログデータ"""
        now = datetime.now()
        return CallLog(
            id="log-123",
            call_uuid="call-456",
            caller_number="+81901234567",
            called_number="+81312345678",
            status="answered",
            direction="inbound",
            started_at=now,
            ended_at=None,
            created_at=now
        )
    
    def test_save_call_log_success(self, storage, sample_call_log):
        """
        正常系: 通話ログが正常に保存される
        """
        storage.save_call_log(sample_call_log)
        
        # 保存されたことを確認
        retrieved = storage.get_call_log(sample_call_log.call_uuid)
        assert retrieved is not None
        assert retrieved.id == sample_call_log.id
        assert retrieved.call_uuid == sample_call_log.call_uuid
    
    def test_save_call_log_with_ended_at(self, storage, sample_call_log):
        """
        正常系: ended_atが設定された通話ログが保存される
        """
        sample_call_log.ended_at = datetime.now()
        storage.save_call_log(sample_call_log)
        
        retrieved = storage.get_call_log(sample_call_log.call_uuid)
        assert retrieved is not None
        assert retrieved.ended_at is not None
    
    def test_save_call_log_updates_existing(self, storage, sample_call_log):
        """
        正常系: 同じIDの通話ログが存在する場合、更新される
        """
        storage.save_call_log(sample_call_log)
        
        # 更新
        updated_call_log = CallLog(
            id=sample_call_log.id,
            call_uuid=sample_call_log.call_uuid,
            caller_number=sample_call_log.caller_number,
            called_number=sample_call_log.called_number,
            status="completed",  # 変更
            direction=sample_call_log.direction,
            started_at=sample_call_log.started_at,
            ended_at=datetime.now(),  # 変更
            created_at=sample_call_log.created_at
        )
        storage.save_call_log(updated_call_log)
        
        # 更新されたことを確認
        retrieved = storage.get_call_log(sample_call_log.call_uuid)
        assert retrieved.status == "completed"
        assert retrieved.ended_at is not None


class TestSQLiteStorageGetCallLog:
    """SQLiteStorage.get_call_log() のテスト"""
    
    @pytest.fixture
    def storage(self):
        """テスト用のSQLiteStorageインスタンス"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            yield SQLiteStorage(db_path)
    
    def test_get_call_log_not_found(self, storage):
        """
        エッジケース: 存在しない通話ログの場合、Noneが返される
        """
        retrieved = storage.get_call_log("non-existent-uuid")
        
        assert retrieved is None
