"""
音楽生成モジュール (Music Generator Module)

留守録の音声をテキストに変換し、Mureka APIで音楽を生成します。
完成したらVonage SMS APIでURLを送信します。
"""

import os
import time
import requests
from typing import Optional, Dict, Any
from pathlib import Path

# OpenAI Whisper用
import openai


class MusicGeneratorError(Exception):
    """音楽生成エラー"""
    pass


class MusicGenerator:
    """
    留守録から音楽を生成するクラス
    
    処理フロー:
    1. 音声ファイルをOpenAI Whisperでテキストに変換
    2. テキストを歌詞としてMureka APIで音楽生成
    3. 完成したらVonage SMS APIでURLを送信
    """
    
    MUREKA_API_BASE = "https://api.mureka.ai/v1"
    
    def __init__(
        self,
        openai_api_key: str,
        mureka_api_key: str,
        vonage_api_key: str,
        vonage_api_secret: str,
        vonage_from_number: str
    ):
        """
        MusicGeneratorを初期化
        
        Args:
            openai_api_key: OpenAI APIキー
            mureka_api_key: Mureka APIキー
            vonage_api_key: Vonage APIキー
            vonage_api_secret: Vonage APIシークレット
            vonage_from_number: SMS送信元電話番号
        """
        self.openai_api_key = openai_api_key
        self.mureka_api_key = mureka_api_key
        self.vonage_api_key = vonage_api_key
        self.vonage_api_secret = vonage_api_secret
        self.vonage_from_number = vonage_from_number
        
        # OpenAIクライアントを初期化
        openai.api_key = openai_api_key
    
    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        音声ファイルをテキストに変換（OpenAI Whisper）
        
        Args:
            audio_file_path: 音声ファイルのパス
        
        Returns:
            変換されたテキスト
        
        Raises:
            MusicGeneratorError: 変換に失敗した場合
        """
        if not os.path.exists(audio_file_path):
            raise MusicGeneratorError(f"音声ファイルが見つかりません: {audio_file_path}")
        
        try:
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            with open(audio_file_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ja"  # 日本語
                )
            
            return transcript.text
            
        except Exception as e:
            raise MusicGeneratorError(f"音声認識に失敗しました: {e}")
    
    def generate_music(
        self,
        lyrics: str,
        prompt: str = "rap, hip-hop, japanese, emotional, rhythmic",
        model: str = "auto",
        max_retries: int = 3,
        retry_delay: int = 30
    ) -> str:
        """
        Mureka APIで音楽を生成
        
        Args:
            lyrics: 歌詞テキスト
            prompt: 音楽スタイルの指示
            model: 使用するモデル
            max_retries: 最大リトライ回数
            retry_delay: リトライ間隔（秒）
        
        Returns:
            生成タスクID
        
        Raises:
            MusicGeneratorError: 生成リクエストに失敗した場合
        """
        if not lyrics or not lyrics.strip():
            raise MusicGeneratorError("歌詞が空です")
        
        # 歌詞をVerse形式にフォーマット
        formatted_lyrics = self._format_lyrics(lyrics)
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.MUREKA_API_BASE}/song/generate",
                    headers={
                        "Authorization": f"Bearer {self.mureka_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "lyrics": formatted_lyrics,
                        "model": model,
                        "prompt": prompt
                    },
                    timeout=30
                )
                
                # レート制限の場合はリトライ
                if response.status_code == 429:
                    error_detail = response.text
                    print(f"429エラー詳細: {error_detail}")
                    if attempt < max_retries - 1:
                        print(f"レート制限。{retry_delay}秒後にリトライ... ({attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise MusicGeneratorError(f"レート制限: {error_detail}")
                
                # その他のエラーの場合も詳細を出力
                if response.status_code >= 400:
                    error_detail = response.text
                    print(f"APIエラー ({response.status_code}): {error_detail}")
                
                response.raise_for_status()
                
                data = response.json()
                task_id = data.get("id")
                
                if not task_id:
                    raise MusicGeneratorError("タスクIDが取得できませんでした")
                
                return task_id
                
            except requests.RequestException as e:
                if attempt < max_retries - 1 and "429" in str(e):
                    print(f"レート制限。{retry_delay}秒後にリトライ... ({attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                raise MusicGeneratorError(f"音楽生成リクエストに失敗しました: {e}")
    
    def check_music_status(self, task_id: str) -> Dict[str, Any]:
        """
        音楽生成タスクのステータスを確認
        
        Args:
            task_id: タスクID
        
        Returns:
            タスク情報（status, audio_url等）
        
        Raises:
            MusicGeneratorError: ステータス確認に失敗した場合
        """
        try:
            response = requests.get(
                f"{self.MUREKA_API_BASE}/song/query/{task_id}",
                headers={
                    "Authorization": f"Bearer {self.mureka_api_key}"
                },
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            raise MusicGeneratorError(f"ステータス確認に失敗しました: {e}")
    
    def wait_for_music(
        self,
        task_id: str,
        timeout: int = 300,
        poll_interval: int = 10
    ) -> Optional[str]:
        """
        音楽生成完了を待機してURLを取得
        
        Args:
            task_id: タスクID
            timeout: タイムアウト秒数
            poll_interval: ポーリング間隔秒数
        
        Returns:
            音楽ファイルのURL、失敗した場合はNone
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = self.check_music_status(task_id)
                status = result.get("status", "")
                
                if status == "succeeded":
                    # 生成された曲のURLを取得
                    choices = result.get("choices", [])
                    if choices and len(choices) > 0:
                        return choices[0].get("url")
                    return None
                
                elif status == "failed":
                    print(f"音楽生成に失敗しました: {result}")
                    return None
                
                # まだ処理中
                time.sleep(poll_interval)
                
            except MusicGeneratorError as e:
                print(f"ステータス確認エラー: {e}")
                time.sleep(poll_interval)
        
        print(f"タイムアウト: {timeout}秒経過しました")
        return None
    
    def send_sms(self, to_number: str, message: str) -> bool:
        """
        Vonage SMS APIでメッセージを送信
        
        Args:
            to_number: 送信先電話番号
            message: メッセージ本文
        
        Returns:
            送信成功した場合True
        """
        try:
            response = requests.post(
                "https://rest.nexmo.com/sms/json",
                data={
                    "api_key": self.vonage_api_key,
                    "api_secret": self.vonage_api_secret,
                    "from": self.vonage_from_number,
                    "to": to_number,
                    "text": message,
                    "type": "unicode"
                },
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            messages = data.get("messages", [])
            
            if messages and messages[0].get("status") == "0":
                return True
            else:
                print(f"SMS送信エラー: {data}")
                return False
                
        except requests.RequestException as e:
            print(f"SMS送信に失敗しました: {e}")
            return False
    
    def process_voicemail(
        self,
        audio_file_path: str,
        caller_number: str,
        music_style: str = "rap, hip-hop, japanese, emotional, rhythmic"
    ) -> Optional[str]:
        """
        留守録を処理して音楽を生成し、SMSで通知
        
        Args:
            audio_file_path: 音声ファイルのパス
            caller_number: 発信者の電話番号（SMS送信先）
            music_style: 音楽スタイル
        
        Returns:
            生成された音楽のURL、失敗した場合はNone
        """
        print(f"留守録処理開始: {audio_file_path}")
        
        # 1. 音声をテキストに変換
        try:
            text = self.transcribe_audio(audio_file_path)
            print(f"音声認識結果: {text}")
        except MusicGeneratorError as e:
            print(f"音声認識エラー: {e}")
            return None
        
        if not text or len(text.strip()) < 5:
            print("音声が短すぎるか認識できませんでした")
            return None
        
        # 2. 音楽を生成
        try:
            task_id = self.generate_music(text, prompt=music_style)
            print(f"音楽生成タスク開始: {task_id}")
        except MusicGeneratorError as e:
            print(f"音楽生成エラー: {e}")
            return None
        
        # 3. 完成を待機
        music_url = self.wait_for_music(task_id)
        
        if not music_url:
            print("音楽生成に失敗しました")
            return None
        
        print(f"音楽生成完了: {music_url}")
        
        # 4. SMSで通知
        message = f"あなたの留守録が音楽になりました！🎵\n{music_url}"
        
        if self.send_sms(caller_number, message):
            print(f"SMS送信完了: {caller_number}")
        else:
            print(f"SMS送信失敗: {caller_number}")
        
        return music_url
    
    def _format_lyrics(self, text: str) -> str:
        """
        テキストを歌詞形式にフォーマット
        
        Args:
            text: 元のテキスト
        
        Returns:
            フォーマットされた歌詞
        """
        # 短いテキストはそのままVerseとして使用
        lines = text.strip().split("。")
        lines = [line.strip() for line in lines if line.strip()]
        
        if len(lines) <= 2:
            return f"[Verse]\n{text}"
        
        # 複数の文がある場合はVerseとChorusに分ける
        mid = len(lines) // 2
        verse_lines = lines[:mid]
        chorus_lines = lines[mid:]
        
        verse = "\n".join(verse_lines)
        chorus = "\n".join(chorus_lines)
        
        return f"[Verse]\n{verse}\n\n[Chorus]\n{chorus}"
