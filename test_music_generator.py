"""
音楽生成機能のテストスクリプト

使用方法:
    python test_music_generator.py <音声ファイルパス> <電話番号>

例:
    python test_music_generator.py recordings/test.mp3 818012345678
"""

import os
import sys
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

def test_transcription(audio_file_path: str):
    """音声認識のみテスト"""
    from src.music_generator import MusicGenerator
    
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("エラー: OPENAI_API_KEY が設定されていません")
        return None
    
    generator = MusicGenerator(
        openai_api_key=openai_api_key,
        mureka_api_key="dummy",
        vonage_api_key="dummy",
        vonage_api_secret="dummy",
        vonage_from_number="dummy"
    )
    
    print(f"音声ファイル: {audio_file_path}")
    print("音声認識を開始...")
    
    try:
        text = generator.transcribe_audio(audio_file_path)
        print(f"\n=== 認識結果 ===")
        print(text)
        print(f"================\n")
        return text
    except Exception as e:
        print(f"エラー: {e}")
        return None


def test_full_pipeline(audio_file_path: str, phone_number: str):
    """フルパイプラインテスト（音声認識→音楽生成→SMS送信）"""
    from src.music_generator import MusicGenerator
    
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    mureka_api_key = os.environ.get("MUREKA_API_KEY")
    vonage_api_key = os.environ.get("VONAGE_API_KEY")
    vonage_api_secret = os.environ.get("VONAGE_API_SECRET")
    vonage_sms_from = os.environ.get("VONAGE_SMS_FROM")
    music_style = os.environ.get("MUSIC_STYLE", "j-pop, emotional, heartfelt, japanese")
    
    missing = []
    if not openai_api_key:
        missing.append("OPENAI_API_KEY")
    if not mureka_api_key:
        missing.append("MUREKA_API_KEY")
    if not vonage_api_key:
        missing.append("VONAGE_API_KEY")
    if not vonage_api_secret:
        missing.append("VONAGE_API_SECRET")
    if not vonage_sms_from:
        missing.append("VONAGE_SMS_FROM")
    
    if missing:
        print(f"エラー: 以下の環境変数が設定されていません: {', '.join(missing)}")
        return
    
    generator = MusicGenerator(
        openai_api_key=openai_api_key,
        mureka_api_key=mureka_api_key,
        vonage_api_key=vonage_api_key,
        vonage_api_secret=vonage_api_secret,
        vonage_from_number=vonage_sms_from
    )
    
    print(f"音声ファイル: {audio_file_path}")
    print(f"送信先電話番号: {phone_number}")
    print(f"音楽スタイル: {music_style}")
    print("\n処理を開始...")
    
    music_url = generator.process_voicemail(
        audio_file_path=audio_file_path,
        caller_number=phone_number,
        music_style=music_style
    )
    
    if music_url:
        print(f"\n成功！音楽URL: {music_url}")
    else:
        print("\n失敗しました")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  音声認識のみ: python test_music_generator.py <音声ファイル>")
        print("  フルテスト:   python test_music_generator.py <音声ファイル> <電話番号>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    if not os.path.exists(audio_file):
        print(f"エラー: ファイルが見つかりません: {audio_file}")
        sys.exit(1)
    
    if len(sys.argv) >= 3:
        phone = sys.argv[2]
        test_full_pipeline(audio_file, phone)
    else:
        test_transcription(audio_file)
