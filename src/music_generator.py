"""
音楽生成モジュール (Music Generator Module)

留守録の音声をテキストに変換し、Udio APIで音楽を生成します。
完成したらVonage SMS APIでURLを送信します。
"""

import os
import time
import logging
import requests
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

import structlog

# OpenAI Whisper用
import openai


# ログ設定
def setup_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """構造化ロガーを設定して取得"""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger(name)


class MusicGeneratorError(Exception):
    """音楽生成エラー"""
    pass


class MusicGenerator:
    """
    留守録から音楽を生成するクラス
    
    処理フロー:
    1. 音声ファイルをOpenAI Whisperでテキストに変換
    2. テキストを歌詞としてUdio APIで音楽生成
    3. 完成したらVonage SMS APIでURLを送信
    """
    
    UDIO_API_BASE = "https://udioapi.pro/api"
    
    def __init__(
        self,
        openai_api_key: str,
        udio_api_key: str,
        vonage_api_key: str,
        vonage_api_secret: str,
        vonage_from_number: str
    ):
        """
        MusicGeneratorを初期化
        
        Args:
            openai_api_key: OpenAI APIキー
            udio_api_key: Udio APIキー
            vonage_api_key: Vonage APIキー
            vonage_api_secret: Vonage APIシークレット
            vonage_from_number: SMS送信元電話番号
        """
        self.openai_api_key = openai_api_key
        self.udio_api_key = udio_api_key
        self.vonage_api_key = vonage_api_key
        self.vonage_api_secret = vonage_api_secret
        self.vonage_from_number = vonage_from_number
        
        # OpenAIクライアントを初期化
        openai.api_key = openai_api_key
        
        # ロガーを初期化
        self.logger = setup_logger(__name__)
        
        self.logger.info(
            "music_generator_initialized",
            udio_api_base=self.UDIO_API_BASE,
            vonage_from_number=vonage_from_number
        )
    
    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        音声ファイルをテキストに変換（OpenAI Whisper）
        """
        self.logger.info(
            "transcribe_audio_start",
            audio_file_path=audio_file_path
        )
        
        if not os.path.exists(audio_file_path):
            self.logger.error(
                "transcribe_audio_file_not_found",
                audio_file_path=audio_file_path
            )
            raise MusicGeneratorError(f"音声ファイルが見つかりません: {audio_file_path}")
        
        file_size = os.path.getsize(audio_file_path)
        self.logger.debug(
            "transcribe_audio_file_info",
            audio_file_path=audio_file_path,
            file_size_bytes=file_size
        )
        
        try:
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            self.logger.info(
                "openai_whisper_request",
                model="whisper-1",
                language="ja"
            )
            
            with open(audio_file_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ja"
                )
            
            self.logger.info(
                "openai_whisper_response",
                text_length=len(transcript.text),
                text_preview=transcript.text[:100] if len(transcript.text) > 100 else transcript.text
            )
            
            return transcript.text
            
        except Exception as e:
            self.logger.error(
                "transcribe_audio_error",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise MusicGeneratorError(f"音声認識に失敗しました: {e}")
    
    def generate_music(
        self,
        lyrics: str,
        style: str = "rap, hip-hop, japanese, emotional, rhythmic",
        title: str = "留守録ソング",
        model: str = "chirp-v3-5",
        max_retries: int = 3,
        retry_delay: int = 10
    ) -> str:
        """
        Udio APIで音楽を生成
        """
        self.logger.info(
            "generate_music_start",
            lyrics_length=len(lyrics),
            style=style,
            title=title,
            model=model
        )
        
        if not lyrics or not lyrics.strip():
            self.logger.error("generate_music_empty_lyrics")
            raise MusicGeneratorError("歌詞が空です")
        
        # 歌詞をフォーマット
        formatted_lyrics = self._format_lyrics(lyrics)
        
        self.logger.debug(
            "generate_music_formatted_lyrics",
            formatted_lyrics=formatted_lyrics
        )
        
        request_body = {
            "prompt": formatted_lyrics,
            "style": style,
            "title": title,
            "model": model,
            "make_instrumental": False
        }
        
        for attempt in range(max_retries):
            try:
                url = f"{self.UDIO_API_BASE}/v2/generate"
                
                self.logger.info(
                    "udio_api_request",
                    url=url,
                    method="POST",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    request_body=request_body
                )
                
                response = requests.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.udio_api_key}",
                        "Content-Type": "application/json"
                    },
                    json=request_body,
                    timeout=60
                )
                
                self.logger.info(
                    "udio_api_response",
                    status_code=response.status_code,
                    response_headers=dict(response.headers),
                    response_body=response.text[:1000] if len(response.text) > 1000 else response.text
                )
                
                # エラーレスポンスの詳細を出力
                if response.status_code >= 400:
                    self.logger.error(
                        "udio_api_error",
                        status_code=response.status_code,
                        response_body=response.text
                    )
                    
                    if response.status_code == 429:
                        if attempt < max_retries - 1:
                            self.logger.warning(
                                "udio_api_rate_limit",
                                retry_delay=retry_delay,
                                attempt=attempt + 1
                            )
                            time.sleep(retry_delay)
                            continue
                        else:
                            raise MusicGeneratorError(f"レート制限: {response.text}")
                
                response.raise_for_status()
                
                data = response.json()
                
                # レスポンス構造を確認
                if data.get("code") != 200:
                    self.logger.error(
                        "udio_api_error_code",
                        code=data.get("code"),
                        message=data.get("message")
                    )
                    raise MusicGeneratorError(f"APIエラー: {data.get('message', 'Unknown error')}")
                
                # workIdを取得（トップレベルまたはdata内）
                work_id = data.get("workId") or data.get("data", {}).get("task_id")
                
                if not work_id:
                    self.logger.error(
                        "udio_api_no_work_id",
                        response_data=data
                    )
                    raise MusicGeneratorError(f"タスクIDが取得できませんでした: {data}")
                
                self.logger.info(
                    "generate_music_task_created",
                    work_id=work_id
                )
                
                return work_id
                
            except requests.RequestException as e:
                self.logger.error(
                    "udio_api_request_error",
                    error=str(e),
                    error_type=type(e).__name__,
                    attempt=attempt + 1
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                raise MusicGeneratorError(f"音楽生成リクエストに失敗しました: {e}")
        
        raise MusicGeneratorError("最大リトライ回数に達しました")
    
    def check_music_status(self, work_id: str) -> Dict[str, Any]:
        """
        音楽生成タスクのステータスを確認
        """
        url = f"{self.UDIO_API_BASE}/v2/feed"
        params = {"workId": work_id}
        
        self.logger.debug(
            "udio_api_status_request",
            url=url,
            method="GET",
            params=params
        )
        
        try:
            response = requests.get(
                url,
                params=params,
                headers={
                    "Authorization": f"Bearer {self.udio_api_key}"
                },
                timeout=30
            )
            
            self.logger.debug(
                "udio_api_status_response",
                status_code=response.status_code,
                response_body=response.text[:500] if len(response.text) > 500 else response.text
            )
            
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("code") != 200:
                self.logger.error(
                    "udio_api_status_error",
                    code=data.get("code"),
                    message=data.get("message")
                )
                raise MusicGeneratorError(f"ステータス確認エラー: {data.get('message', 'Unknown error')}")
            
            result = data.get("data", {})
            
            self.logger.info(
                "udio_api_status_result",
                work_id=work_id,
                type=result.get("type"),
                has_response_data=bool(result.get("response_data"))
            )
            
            return result
            
        except requests.RequestException as e:
            self.logger.error(
                "udio_api_status_request_error",
                error=str(e),
                work_id=work_id
            )
            raise MusicGeneratorError(f"ステータス確認に失敗しました: {e}")
    
    def wait_for_music(
        self,
        work_id: str,
        timeout: int = 300,
        poll_interval: int = 10
    ) -> Optional[str]:
        """
        音楽生成完了を待機してURLを取得
        """
        self.logger.info(
            "wait_for_music_start",
            work_id=work_id,
            timeout=timeout,
            poll_interval=poll_interval
        )
        
        start_time = time.time()
        poll_count = 0
        
        while time.time() - start_time < timeout:
            poll_count += 1
            elapsed = int(time.time() - start_time)
            
            try:
                result = self.check_music_status(work_id)
                status_type = result.get("type", "")
                
                self.logger.info(
                    "wait_for_music_poll",
                    work_id=work_id,
                    poll_count=poll_count,
                    elapsed_seconds=elapsed,
                    status_type=status_type
                )
                
                if status_type == "SUCCESS":
                    response_data = result.get("response_data", [])
                    if response_data and len(response_data) > 0:
                        audio_url = response_data[0].get("audio_url")
                        if audio_url:
                            self.logger.info(
                                "wait_for_music_success",
                                work_id=work_id,
                                audio_url=audio_url,
                                total_time_seconds=elapsed
                            )
                            return audio_url
                    
                    self.logger.error(
                        "wait_for_music_no_url",
                        work_id=work_id,
                        response_data=response_data
                    )
                    return None
                
                elif status_type == "FAILED":
                    error_msg = ""
                    if result.get("response_data"):
                        error_msg = result["response_data"][0].get("error_message", "Unknown error")
                    
                    self.logger.error(
                        "wait_for_music_failed",
                        work_id=work_id,
                        error_message=error_msg,
                        result=result
                    )
                    return None
                
                time.sleep(poll_interval)
                
            except MusicGeneratorError as e:
                self.logger.warning(
                    "wait_for_music_poll_error",
                    work_id=work_id,
                    error=str(e),
                    poll_count=poll_count
                )
                time.sleep(poll_interval)
        
        self.logger.error(
            "wait_for_music_timeout",
            work_id=work_id,
            timeout=timeout,
            poll_count=poll_count
        )
        return None
    
    def send_sms(self, to_number: str, message: str) -> bool:
        """
        Vonage SMS APIでメッセージを送信
        """
        url = "https://rest.nexmo.com/sms/json"
        
        request_data = {
            "api_key": self.vonage_api_key,
            "api_secret": "***",  # ログには出さない
            "from": self.vonage_from_number,
            "to": to_number,
            "text": message,
            "type": "unicode"
        }
        
        self.logger.info(
            "vonage_sms_request",
            url=url,
            to_number=to_number,
            from_number=self.vonage_from_number,
            message_length=len(message)
        )
        
        try:
            response = requests.post(
                url,
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
            
            self.logger.info(
                "vonage_sms_response",
                status_code=response.status_code,
                response_body=response.text
            )
            
            response.raise_for_status()
            
            data = response.json()
            messages = data.get("messages", [])
            
            if messages and messages[0].get("status") == "0":
                self.logger.info(
                    "vonage_sms_success",
                    to_number=to_number,
                    message_id=messages[0].get("message-id")
                )
                return True
            else:
                self.logger.error(
                    "vonage_sms_failed",
                    to_number=to_number,
                    response_data=data
                )
                return False
                
        except requests.RequestException as e:
            self.logger.error(
                "vonage_sms_error",
                error=str(e),
                to_number=to_number
            )
            return False
    
    def process_voicemail(
        self,
        audio_file_path: str,
        caller_number: str,
        music_style: str = "rap, hip-hop, japanese, emotional, rhythmic"
    ) -> Optional[str]:
        """
        留守録を処理して音楽を生成し、SMSで通知
        """
        process_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.logger.info(
            "process_voicemail_start",
            process_id=process_id,
            audio_file_path=audio_file_path,
            caller_number=caller_number,
            music_style=music_style
        )
        
        # 1. 音声をテキストに変換
        try:
            text = self.transcribe_audio(audio_file_path)
        except MusicGeneratorError as e:
            self.logger.error(
                "process_voicemail_transcribe_error",
                process_id=process_id,
                error=str(e)
            )
            return None
        
        if not text or len(text.strip()) < 5:
            self.logger.warning(
                "process_voicemail_text_too_short",
                process_id=process_id,
                text_length=len(text) if text else 0
            )
            return None
        
        # 2. 音楽を生成
        try:
            work_id = self.generate_music(text, style=music_style)
        except MusicGeneratorError as e:
            self.logger.error(
                "process_voicemail_generate_error",
                process_id=process_id,
                error=str(e)
            )
            return None
        
        # 3. 完成を待機
        music_url = self.wait_for_music(work_id)
        
        if not music_url:
            self.logger.error(
                "process_voicemail_no_music_url",
                process_id=process_id,
                work_id=work_id
            )
            return None
        
        # 4. SMSで通知
        message = f"あなたの留守録が音楽になりました！🎵\n{music_url}"
        sms_sent = self.send_sms(caller_number, message)
        
        self.logger.info(
            "process_voicemail_complete",
            process_id=process_id,
            music_url=music_url,
            sms_sent=sms_sent
        )
        
        return music_url
    
    def _format_lyrics(self, text: str) -> str:
        """
        テキストを歌詞形式にフォーマット
        """
        lines = text.strip().split("。")
        lines = [line.strip() for line in lines if line.strip()]
        
        if len(lines) <= 2:
            return f"[Verse]\n{text}"
        
        mid = len(lines) // 2
        verse_lines = lines[:mid]
        chorus_lines = lines[mid:]
        
        verse = "\n".join(verse_lines)
        chorus = "\n".join(chorus_lines)
        
        return f"[Verse]\n{verse}\n\n[Chorus]\n{chorus}"
