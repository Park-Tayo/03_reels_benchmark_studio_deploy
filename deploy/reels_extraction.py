import yt_dlp
import tempfile
import os
from pathlib import Path
import subprocess
import openai
from api_config import get_api_config
import time
from functools import wraps
import requests
from datetime import datetime

# 상대 경로로 변경 (스트림릿 클라우드 호환)
BASE_DIR = Path(__file__).parent.parent

# 임시 파일 디렉토리 설정
TEMP_DIR = Path(tempfile.gettempdir()) / "reels_benchmark"
os.makedirs(TEMP_DIR, exist_ok=True)

def get_whisper_model():
    # 위스퍼 모델 import 제거
    # import whisper 제거
    return None

def timer_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"[Timer] {func.__name__}: {end_time - start_time:.2f}초")
        return result
    return wrapper

@timer_decorator
def extract_audio_from_url(url):
    try:
        # 임시 파일 경로를 플랫폼 독립적으로 생성
        temp_audio = TEMP_DIR / f"audio_{int(time.time())}.wav"
        
        command = [
            'ffmpeg',
            '-i', url,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            '-y',
            str(temp_audio)  # Path 객체를 문자열로 변환
        ]
        
        subprocess.run(command, check=True, capture_output=True)
        return str(temp_audio)
    except Exception as e:
        print(f"오디오 추출 실패: {e}")
        return None

@timer_decorator
def transcribe_video(video_url):
    try:
        audio_path = extract_audio_from_url(video_url)
        if not audio_path:
            return ""
            
        # OpenAI API를 사용한 음성 인식
        api_config = get_api_config()
        client = openai.OpenAI(api_key=api_config["api_key"])
        
        with open(audio_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ko"  # 한국어 설정
            )
        
        os.remove(audio_path)
        return transcript.text
        
    except Exception as e:
        print(f"전사 오류: {e}")
        return ""

@timer_decorator
def extract_reels_info(url, video_analysis=None):
    try:
        ydl_opts = {
            'format': 'best',
            'extract_flat': True,  # 최소 정보만 먼저 시도
            'quiet': False,  # 디버그 메시지 활성화
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # 각 필드 개별적으로 시도하고 결과 출력
            print("\n=== 접근 가능한 정보 테스트 ===")
            fields_to_test = [
                'webpage_url_basename',
                'timestamp',
                'description',
                'duration',
                'like_count',
                'comment_count',
                'channel',
                'url'
            ]
            
            available_data = {}
            for field in fields_to_test:
                try:
                    value = info.get(field)
                    available_data[field] = value
                    print(f"✅ {field}: {value}")
                except Exception as e:
                    print(f"❌ {field}: {str(e)}")
            
            # 성공적으로 가져온 데이터만으로 결과 구성
            reels_info = {
                'shortcode': available_data.get('webpage_url_basename', ''),
                'date': datetime.fromtimestamp(available_data.get('timestamp', 0)).strftime('%Y-%m-%d') if available_data.get('timestamp') else '',
                'caption': available_data.get('description', ''),
                'view_count': 0,
                'video_duration': available_data.get('duration', 0),
                'likes': available_data.get('like_count', 0),
                'comments': available_data.get('comment_count', 0),
                'owner': available_data.get('channel', ''),
                'video_url': available_data.get('url', '')
            }
            
            return reels_info
            
    except Exception as e:
        print(f"전체 오류: {str(e)}")
        return f"Error: {str(e)}"

@timer_decorator
def process_transcript_and_caption(transcript, caption, video_analysis):
    """스크립트와 캡션의 번역/정제를 하나의 GPT 호출로 통합"""
    try:
        api_config = get_api_config()
        client = openai.OpenAI(api_key=api_config["api_key"])
        
        prompt = f"""
        다음은 영상의 스크립트와 캡션입니다. 각각에 대해 다음 작업을 수행해주세요:
        1. 영어로 된 경우 한국어로 번역 (단, 전문용어/브랜드명/해시태그는 원문 유지)
        2. 이모티콘과 특수문자는 그대로 유지
        3. 전체적으로 자연스러운 한국어로 정제
        
        원본 스크립트:
        {transcript}
        
        원본 캡션:
        {caption}
        
        영상 분석 내용:
        - 초반 3초 (카피라이팅): {video_analysis.get('intro_copy', '')}
        - 초반 3초 (영상 구성): {video_analysis.get('intro_structure', '')}
        - 나레이션: {video_analysis.get('narration', '')}
        
        다음 형식으로 결과를 반환해주세요:
        ---스크립트---
        [정제된 스크립트]
        ---캡션---
        [정제된 캡션]
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "당신은 전문 번역가이자 스크립트 교정 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        result = response.choices[0].message.content.strip()
        
        # 결과 파싱
        transcript_part = result.split("---캡션---")[0].replace("---스크립트---", "").strip()
        caption_part = result.split("---캡션---")[1].strip()
        
        return {
            "transcript": transcript_part,
            "caption": caption_part
        }
        
    except Exception as e:
        print(f"텍스트 처리 중 오류 발생: {e}")
        return {
            "transcript": transcript,
            "caption": caption
        }

@timer_decorator
def download_video(url):
    try:
        ydl_opts = {
            'format': 'best',
            'outtmpl': str(TEMP_DIR / '%(id)s.%(ext)s'),  # 임시 디렉토리에 저장
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info['url']
            
            # 임시 파일 생성
            temp_video = TEMP_DIR / f"video_{int(time.time())}.mp4"
            
            # 비디오 다운로드
            print("📥 비디오 다운로드 중...")
            response = requests.get(video_url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(temp_video, 'wb') as video_file:
                if total_size == 0:
                    video_file.write(response.content)
                else:
                    downloaded = 0
                    for data in response.iter_content(chunk_size=4096):
                        downloaded += len(data)
                        video_file.write(data)
                        
            print("✅ 비디오 다운로드 완료!")
            return str(temp_video)
            
    except Exception as e:
        print(f"⚠️ 다운로드 오류: {str(e)}")
        return None