"""
音楽生成機能のテストスクリプト

使用方法:
    python test_music_generator.py [音声ファイルパス]
    
例:
    python test_music_generator.py recordings/test.mp3
"""

import os
import sys
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

def test_transcription_only(audio_file: str):
    """音声認識のみテスト"""
    from src.music_generator import MusicGenerator
    
    print("=" * 50)
    print("音声認識テスト")
    print("=" * 50)
    
    mg = MusicGenerator(
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        mureka_api_key=os.getenv('MUREKA_API_KEY'),
        vonage_api_key=os.getenv('VONAGE_API_KEY'),
        vonage_api_secret=os.getenv('VONAGE_API_SECRET'),
        vonage_from_number=os.getenv('VONAGE_SMS_FROM', '')
    )
    
    try:
        text = mg.transcribe_audio(audio_file)
        print(f"✅ 音声認識成功!")
        print(f"認識結果: {text}")
        print(f"文字数: {len(text)}")
        return text
    except Exception as e:
        print(f"❌ 音声認識失敗: {e}")
        return None


def test_music_generation(lyrics: str):
    """音楽生成のみテスト"""
    from src.music_generator import MusicGenerator
    
    print("\n" + "=" * 50)
    print("音楽生成テスト")
    print("=" * 50)
    
    mg = MusicGenerator(
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        mureka_api_key=os.getenv('MUREKA_API_KEY'),
        vonage_api_key=os.getenv('VONAGE_API_KEY'),
        vonage_api_secret=os.getenv('VONAGE_API_SECRET'),
        vonage_from_number=os.getenv('VONAGE_SMS_FROM', '')
    )
    
    # 歌詞をフォーマット
    formatted = mg._format_lyrics(lyrics)
    print(f"フォーマット済み歌詞:\n{formatted}")
    
    music_style = os.getenv('MUSIC_STYLE', 'rap, hip-hop, japanese, emotional, rhythmic')
    print(f"\n音楽スタイル: {music_style}")
    
    try:
        print("\nMureka APIにリクエスト送信中...")
        task_id = mg.generate_music(lyrics, prompt=music_style)
        print(f"✅ タスク作成成功! タスクID: {task_id}")
        
        print("\n音楽生成完了を待機中...")
        music_url = mg.wait_for_music(task_id, timeout=300, poll_interval=10)
        
        if music_url:
            print(f"✅ 音楽生成完了!")
            print(f"URL: {music_url}")
            return music_url
        else:
            print("❌ 音楽生成失敗またはタイムアウト")
            return None
            
    except Exception as e:
        print(f"❌ 音楽生成エラー: {e}")
        return None


def test_full_pipeline(audio_file: str, phone_number: str = None):
    """フルパイプラインテスト"""
    from src.music_generator import MusicGenerator
    
    print("\n" + "=" * 50)
    print("フルパイプラインテスト")
    print("=" * 50)
    
    mg = MusicGenerator(
        openai_api_key=os.getenv('OPENAI_API_KEY'),
        mureka_api_key=os.getenv('MUREKA_API_KEY'),
        vonage_api_key=os.getenv('VONAGE_API_KEY'),
        vonage_api_secret=os.getenv('VONAGE_API_SECRET'),
        vonage_from_number=os.getenv('VONAGE_SMS_FROM', '')
    )
    
    music_style = os.getenv('MUSIC_STYLE', 'rap, hip-hop, japanese, emotional, rhythmic')
    
    if not phone_number:
        phone_number = os.getenv('TEST_PHONE_NUMBER', '')
    
    if not phone_number:
        print("⚠️ SMS送信先電話番号が設定されていません")
        print("TEST_PHONE_NUMBER環境変数を設定するか、引数で指定してください")
    
    result = mg.process_voicemail(
        audio_file_path=audio_file,
        caller_number=phone_number,
        music_style=music_style
    )
    
    if result:
        print(f"\n✅ 処理完了! 音楽URL: {result}")
    else:
        print("\n❌ 処理失敗")
    
    return result


def check_env():
    """環境変数の確認"""
    print("=" * 50)
    print("環境変数チェック")
    print("=" * 50)
    
    required = {
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'MUREKA_API_KEY': os.getenv('MUREKA_API_KEY'),
        'VONAGE_API_KEY': os.getenv('VONAGE_API_KEY'),
        'VONAGE_API_SECRET': os.getenv('VONAGE_API_SECRET'),
    }
    
    optional = {
        'VONAGE_SMS_FROM': os.getenv('VONAGE_SMS_FROM'),
        'MUSIC_STYLE': os.getenv('MUSIC_STYLE'),
        'ENABLE_MUSIC_GENERATION': os.getenv('ENABLE_MUSIC_GENERATION'),
    }
    
    all_ok = True
    for key, value in required.items():
        if value:
            masked = value[:4] + '...' + value[-4:] if len(value) > 8 else '***'
            print(f"✅ {key}: {masked}")
        else:
            print(f"❌ {key}: 未設定")
            all_ok = False
    
    print("\nオプション設定:")
    for key, value in optional.items():
        if value:
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: 未設定")
    
    return all_ok


if __name__ == "__main__":
    print("\n🎵 音楽生成テストスクリプト 🎵\n")
    
    # 環境変数チェック
    if not check_env():
        print("\n❌ 必須の環境変数が設定されていません")
        sys.exit(1)
    
    # 引数チェック
    if len(sys.argv) < 2:
        print("\n使用方法:")
        print("  python test_music_generator.py <音声ファイルパス> [電話番号]")
        print("\n例:")
        print("  python test_music_generator.py recordings/test.mp3")
        print("  python test_music_generator.py recordings/test.mp3 818012345678")
        print("\nテストモード:")
        print("  --transcribe-only: 音声認識のみ")
        print("  --generate-only: 音楽生成のみ（テスト歌詞使用）")
        sys.exit(0)
    
    audio_file = sys.argv[1]
    
    if audio_file == "--generate-only":
        # 音楽生成のみテスト（テスト歌詞使用）
        test_lyrics = "今日は天気がいいですね。散歩に行きたいです。"
        test_music_generation(test_lyrics)
    elif audio_file == "--transcribe-only" and len(sys.argv) > 2:
        # 音声認識のみテスト
        test_transcription_only(sys.argv[2])
    elif not os.path.exists(audio_file):
        print(f"\n❌ ファイルが見つかりません: {audio_file}")
        sys.exit(1)
    else:
        # フルテスト
        phone = sys.argv[2] if len(sys.argv) > 2 else None
        
        # まず音声認識
        text = test_transcription_only(audio_file)
        
        if text:
            # 音楽生成
            url = test_music_generation(text)
