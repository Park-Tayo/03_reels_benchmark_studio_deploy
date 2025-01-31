import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# API 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def get_api_config():
    if not OPENAI_API_KEY:
        raise ValueError("API 설정이 없습니다. .env 파일을 확인해주세요.")
    
    return {
        "api_key": OPENAI_API_KEY
    } 