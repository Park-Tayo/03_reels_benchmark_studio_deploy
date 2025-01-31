import streamlit as st
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from reels_extraction import download_video, extract_reels_info
import os
from dotenv import load_dotenv
from api_config import get_api_config
import requests
import openai
import re
import time
from urllib.parse import urlparse
import yt_dlp

# .env 파일 로드
load_dotenv()

# API 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 페이지 기본 설정
st.set_page_config(
    page_title="✨ 릴스 벤치마킹 스튜디오",
    page_icon="🎥",
    layout="centered"
)

# 스타일 설정
st.markdown("""
    <style>
    /* 전체 페이지 스타일 */
    .main {
        max-width: 1200px;
        margin: 0 auto;
        padding: 2rem;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* 브랜드 로고 */
    .brand-logo {
        position: fixed;
        top: 20px;
        right: 20px;
        font-size: 14px;
        color: #1c1c1e;
        letter-spacing: 0.5px;
        font-weight: 500;
    }
    
    /* 메인 타이틀 */
    .title-container {
        text-align: left;
        margin: 1rem 0;
        padding-bottom: 1rem;
        border-bottom: 2px solid #f1f1f1;
    }
    
    .title-container h1 {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1c1c1e;
        margin-bottom: 0.5rem;
    }
    
    /* 섹션 헤더 */
    .section-header {
        margin: 2.5rem 0 1.5rem 0;
        padding: 0;
        color: #1c1c1e;
        font-size: 1.5rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .section-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        background: linear-gradient(45deg, #405DE6, #5851DB);
        color: white;
        border-radius: 50%;
        font-size: 14px;
        font-weight: 600;
        margin-right: 8px;
    }
    
    /* 입력 필드 스타일링 */
    .stTextInput > div > div {
        border-radius: 12px !important;
        border: 1px solid #e6e6e6 !important;
        padding: 0.5rem !important;
    }
    
    .stTextInput > div > div:focus-within {
        border-color: #405DE6 !important;
        box-shadow: 0 0 0 1px #405DE6 !important;
    }
    
    /* 비디오 컨테이너 */
    .video-container {
        background: white;
        border-radius: 20px;
        padding: 1.5rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        margin: 2rem 0;
    }
    
    .stVideo {
        width: 100%;
        max-width: 400px !important;
        margin: 0 auto;
        border-radius: 12px;
        overflow: hidden;
    }
    
    /* 버튼 스타일링 */
    .stButton > button {
        background: linear-gradient(45deg, #405DE6, #5851DB) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.5rem 2rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(64,93,230,0.2) !important;
    }
    
    /* 확장 패널 스타일링 */
    .streamlit-expanderHeader {
        background: white !important;
        border-radius: 12px !important;
        border: 1px solid #e6e6e6 !important;
    }
    
    /* 폼 컨테이너 */
    .form-container {
        background: white;
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        margin: 2rem 0;
    }
    
    /* 분석 결과 섹션 스타일링 */
    .analysis-section {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    .section-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1c1c1e;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .subsection-title {
        font-size: 1.4rem;
        font-weight: 600;
        color: #1c1c1e;
        margin: 1rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .info-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.5rem;
    }
    
    .info-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 1rem;
    }
    
    .info-title {
        font-weight: 600;
        color: #405DE6;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .stProgress > div > div > div {
        background: linear-gradient(45deg, #405DE6, #5851DB) !important;
    }
    .progress-label {
        text-align: center;
        color: #1c1c1e;
        font-weight: 500;
        margin-bottom: 5px;
    }
    .step-container {
        margin-bottom: 20px;
    }
    </style>
    
    <div class="brand-logo">HANSHIN GROUP</div>
""", unsafe_allow_html=True)

def normalize_instagram_url(url):
    """
    입력된 인스타그램 URL을 '/p/{ID}/' 형식으로 변환합니다.
    쿼리 파라미터와 기타 불필요한 부분을 제거합니다.
    """
    try:
        from urllib.parse import urlparse

        parsed_url = urlparse(url)
        path_parts = parsed_url.path.strip('/').split('/')

        if len(path_parts) >= 2:
            if path_parts[0] in ['reel', 'tv', 'p']:
                shortcode = path_parts[1]
                normalized_url = f"https://www.instagram.com/p/{shortcode}/"
                return normalized_url
        return url  # 변경이 필요 없는 다른 형식의 URL

    except Exception as e:
        st.error(f"URL 정규화 중 오류 발생: {str(e)}")
        return url

def is_valid_instagram_url(url):
    # Instagram URL 유효성 검사
    instagram_pattern = r'https?://(?:www\.)?instagram\.com/(?:p|reel)/[a-zA-Z0-9_-]+'
    return bool(re.match(instagram_pattern, url))

def get_video_url(url, username=None, password=None):
    try:
        ydl_opts = {
            'format': 'best',
            'extract_flat': True,
        }
        
        # 로그인 정보가 있으면 추가
        if username and password:
            ydl_opts.update({
                'username': username,
                'password': password,
            })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('url')
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def create_input_form():
    # 타이틀 섹션
    st.markdown('<div class="title-container"><h1>✨ 릴스 벤치마킹 스튜디오</h1></div>', unsafe_allow_html=True)
    
    # 1. 벤치마킹 섹션
    st.markdown("""
        <div class="section-header">
            <span class="section-number">1</span>
            벤치마킹 정보 입력
        </div>
    """, unsafe_allow_html=True)
    
    # URL을 세션 상태로 관리
    if 'url' not in st.session_state:
        st.session_state.url = ''
    
    # URL 입력 필드 (불필요한 컨테이너 제거)
    url = st.text_input("✨ 릴스 URL을 입력해주세요", value=st.session_state.url)
    
    # URL 입력 버튼 추가
    url_submit = st.button("URL 입력")
    
    # 폼 데이터를 세션 상태로 관리
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            'video_intro_copy': '',
            'video_intro_structure': '',
            'narration': '',
            'music': '',
            'font': ''
        }
    
    # URL이 입력되었거나 URL 입력 버튼이 클릭되었을 때 처리
    if url and (url_submit or True):
        video_url = get_video_url(url)
        if video_url:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                try:
                    st.video(video_url)
                except:
                    st.error("동영상을 불러올 수 없습니다.")
            
            with col2:
                # 폼 추가
                with st.form(key='video_analysis_form'):
                    st.markdown("""
                        <style>
                        /* 영상 분석 섹션 헤더 스타일링 */
                        .analysis-header {
                            margin: 1rem 0 1rem 0 !important;  /* 상하 여백 최소화 */
                            padding: 0 !important;
                            color: #1c1c1e;
                            font-size: 1.5rem;
                            font-weight: 600;
                            display: flex;
                            align-items: center;
                        }
                        
                        /* 폼 스타일링 */
                        .stForm {
                            margin-top: 0 !important;
                            padding-top: 0 !important;
                        }
                        
                        /* 폼 제출 버튼 */
                        .stForm [data-testid="stFormSubmitButton"] > button {
                            background: linear-gradient(45deg, #405DE6, #5851DB) !important;
                            color: white !important;
                            border: none !important;
                            border-radius: 12px !important;
                            padding: 0.5rem 2rem !important;
                            font-weight: 600 !important;
                            width: 100% !important;
                            transition: all 0.3s ease !important;
                        }
                        
                        .stForm [data-testid="stFormSubmitButton"] > button:hover {
                            transform: translateY(-2px) !important;
                            box-shadow: 0 4px 12px rgba(64,93,230,0.2) !important;
                        }
                        </style>
                        
                        <div class="analysis-header">
                            <span class="section-number">📊</span>
                            영상 분석
                        </div>
                    """, unsafe_allow_html=True)
                    
                    st.text_area(
                        "**초반 3초 (카피라이팅) 설명**",
                        value=st.session_state.form_data['video_intro_copy'],
                        height=68,
                        help="1. 🎯 구체적 수치 ('월 500만원', '3일 만에' 등)\n"
                             "2. 🧠 뇌 충격 ('망하는 과정', '실패한 이유' 등)\n"
                             "3. 💡 이익/손해 강조 ('놓치면 후회', '꼭 알아야 할' 등)\n"
                             "4. 👑 권위 강조 ('현직 대기업 임원', '10년 경력' 등)\n"
                             "5. ✨ 예시: '현직 인사팀장이 알려주는 연봉 3천 협상법'"
                    )
                    
                    st.text_area(
                        "**초반 3초 (영상 구성) 설명**",
                        value=st.session_state.form_data['video_intro_structure'],
                        height=68,
                        help="1. 💥 상식 파괴 (예상 밖의 장면)\n"
                             "2. 🎬 결과 먼저 보여주기 (Before & After)\n"
                             "3. ⚠️ 부정적 상황 강조\n"
                             "4. 🤝 공감 유도 (일상적 고민/불편함)\n"
                             "5. 📱 예시: '출근 시간에 편하게 누워서 일하는 직원들 모습'"
                    )
                    
                    st.text_input(
                        "**나레이션 설명**",
                        value=st.session_state.form_data['narration'],
                        help="1. 🎤 목소리 특징 (성별, 연령대, 톤)\n"
                             "2. 💬 말하기 스타일 (전문적/친근한)\n"
                             "3. 🎵 음질 상태 (노이즈 없는 깨끗한 음질)\n"
                             "4. ✅️ 예시: '20대 여성의 친근한 톤, 깨끗한 마이크 음질'"
                    )
                    
                    st.text_input(
                        "**음악 설명**",
                        value=st.session_state.form_data['music'],
                        help="1. 🎵 트렌디한 정도 (최신 유행 BGM)\n"
                             "2. 🎶 영상과의 조화 (리듬감, 분위기)\n"
                             "3. 🎼 장르 및 템포\n"
                             "4. 🎧 예시: '트렌디한 K-pop, 영상의 템포와 잘 맞는 리듬'"
                    )
                    
                    st.text_input(
                        "**폰트 설명**",
                        value=st.session_state.form_data['font'],
                        help="1. 📝 폰트 종류 (고딕체, 손글씨체 등)\n"
                             "2. ✒️ 강조 요소 (굵기, 크기, 테두리)\n"
                             "3. 👀 가독성 정도\n"
                             "4. 💫 예시: '눈에 띄는 굵은 글씨, 흰색 테두리, 노란색 배경'"
                    )
                    
                    # 폼 제출 버튼
                    st.form_submit_button("분석 내용 저장")
            
            # URL이 입력되고 동영상이 성공적으로 로드된 경우에만 나머지 섹션 표시
            st.markdown("""
                <div class="section-header">
                    <span class="section-number">2</span>
                    내 콘텐츠 정보 입력
                </div>
            """, unsafe_allow_html=True)
            topic = st.text_area("제작할 콘텐츠에 대해 자유롭게 입력해주세요", height=68)
            
            # 분석 시작 버튼
            if st.button("분석 시작"):
                if not url:
                    st.warning("URL을 입력해주세요.")
                    return None
                
                with st.spinner("분석 중... (약 2분 소요)"):
                    # 캐시된 결과 확인
                    results = get_cached_analysis(url, {
                        "url": url,
                        "video_analysis": {
                            "intro_copy": st.session_state.form_data['video_intro_copy'],
                            "intro_structure": st.session_state.form_data['video_intro_structure'],
                            "narration": st.session_state.form_data['narration'],
                            "music": st.session_state.form_data['music'],
                            "font": st.session_state.form_data['font']
                        },
                        "content_info": {
                            "topic": topic
                        }
                    })
                    
                    if results:
                        display_analysis_results(results["analysis"], results["reels_info"])
                    
                    return None
        else:
            st.error("Instagram URL에서 동영상을 찾을 수 없습니다.")
    
    return {
        "url": url,
        "video_analysis": {
            "intro_copy": st.session_state.form_data['video_intro_copy'],
            "intro_structure": st.session_state.form_data['video_intro_structure'],
            "narration": st.session_state.form_data['narration'],
            "music": st.session_state.form_data['music'],
            "font": st.session_state.form_data['font']
        },
        "content_info": {
            "topic": topic if 'topic' in locals() else ""
        }
    }

@st.cache_data(ttl=3600)
def analyze_with_gpt4(info, input_data):
    try:
        api_config = get_api_config()
        client = openai.OpenAI(api_key=api_config["api_key"])
        
        messages = [
            {
                "role": "system",
                "content": """
                당신은 릴스 분석 전문가입니다. 다음 형식으로 분석 결과를 제공해주세요. 
                각 항목에 대해 ✅/❌를 표시하고, 그 판단의 근거가 되는 스크립트나 캡션의 구체적인 내용을 인용해주세요. 
                여기서 모수란 이 내용이 얼마나 많은 사람들의 관심을 끌 수 있는지에 대한 것입니다.
                문제 해결이란 시청자가 갖고 있는 문제를 해결해줄 수 있는지에 대한 것입니다:

                # 1. 주제: 
                - **설명: (이 영상의 주제에 대한 내용)**
                - ✅/❌ **공유 및 저장**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **모수**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **문제해결**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **욕망충족**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **흥미유발**: 스크립트/캡션 중 해당 내용

                # 2. 초반 3초
                ## 카피라이팅 :
                - **설명: (이 영상의 초반 3초 카피라이팅에 대한 내용)**
                - ✅/❌ **구체적 수치**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **뇌 충격**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **이익, 손해 강조**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **권위 강조**: 스크립트/캡션 중 해당 내용

                ## 영상 구성 : 
                - **설명: (이 영상의 초반 3초 영상 구성에 대한 내용)**
                - ✅/❌ **상식 파괴**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **결과 먼저**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **부정 강조**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **공감 유도**: 스크립트/캡션 중 해당 내용

                # 3. 내용 구성: 
                - **설명: (이 영상의 스크립트/캡션의 전체적인 내용 구성에 대한 내용)**
                - ✅/❌ **문제해결**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **호기심 유발**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **행동 유도**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **스토리**: 스크립트/캡션 중 해당 내용
                - ✅/❌ **제안**: 스크립트/캡션 중 해당 내용

                # 4. 개선할 점:
                - ❌ **(항목명)**: 개선할 점 설명 추가 ex. 스크립트/캡션 예시
                
                # 5. 적용할 점:
                - ✅ **(항목명)**: 적용할 점 설명 추가 ex. 스크립트/캡션 중 해당 내용

                # 6. 벤치마킹 적용 기획:
                {f'''
                - 입력하신 주제 "{input_data["content_info"]["topic"]}"에 대한 벤치마킹 적용 기획입니다.
                - 위에서 체크(✅)된 항목들을 모두 반영하여 벤치마킹한 내용입니다.
                
                [시스템 참고용 - 출력하지 말 것]
                - 스크립트: {info['refined_transcript']}
                - 캡션: {info['caption']}
                
                위 스크립트와 캡션을 최대한 유사하게 벤치마킹하여 다음과 같이 작성했습니다:
                
                ## 🎙️ 1. 스크립트 예시:
                [원본 스크립트의 문장 구조, 호흡, 강조점을 거의 그대로 활용하되 새로운 주제에 맞게 변경.
                예를 들어 원본이 "이것 하나만 있으면 ~~" 구조라면, 새로운 주제도 동일한 구조 사용]

                ## ✏️ 2. 캡션 예시:
                [원본 캡션의 구조를 거의 그대로 활용.
                예를 들어 원본이 "✨꿀팁 공개✨" 시작이라면, 새로운 캡션도 동일한 구조 사용.
                이모지, 해시태그 스타일도 원본과 동일하게 구성]

                ## 🎬 3. 영상 기획:
                원본 영상의 구성을 최대한 유사하게 벤치마킹하되, 다음 요소들을 추가/보완했습니다:

                1. **🎯 도입부** (3초):
                   - 💥 **뇌 충격을 주는 구체적 수치 활용** (스크립트/캡션 예시 내용)
                   - 🔄 **상식을 깨는 내용으로 시작** (스크립트/캡션 예시 내용)
                   - ⭐ **결과를 먼저 보여주는 방식 적용** (스크립트/캡션 예시 내용)
                   
                2. **📝 전개**:
                   - **문제 해결형 구조 적용:**
                     * ❓ **명확한 문제 제시** (스크립트/캡션 예시 내용)
                     * ✅ **구체적인 해결책 제시** (스크립트/캡션 예시 내용)
                   - **시청 지속성 확보:**
                     * 🎙️ **나레이션과 영상의 일치성 유지** (스크립트/캡션 예시 내용)
                     * 🎵 **트렌디한 BGM 활용** (스크립트/캡션 예시 내용)
                     * 📹 **고화질 영상 품질 유지** (스크립트/캡션 예시 내용)
                   
                3. **🔚 마무리**:
                   - **행동 유도 요소 포함:**
                     * 💾 **저장/공유 유도 멘트** (스크립트/캡션 예시 내용)
                     * 👥 **팔로우 제안** (스크립트/캡션 예시 내용)
                   - **캡션 최적화:**
                     * 🎣 **첫 줄 후킹** (스크립트/캡션 예시 내용)
                     * 📑 **단락 구분으로 가독성 확보** (스크립트/캡션 예시 내용)
                     * 📊 **구체적 수치/권위 요소 포함** (스크립트/캡션 예시 내용)
                ''' if input_data["content_info"]["topic"] else "주제가 입력되지 않았습니다. 구체적인 기획을 위해 주제를 입력해주세요."}
                """
            },
            {
                "role": "user",
                "content": f"""
                다음 릴스를 분석하고, 입력된 주제에 맞게 벤치마킹 기획을 해주세요:
                
                스크립트: {info['refined_transcript']}
                캡션: {info['caption']}
                
                사용자 입력 정보:
                - 초반 3초 카피라이팅: {input_data['video_analysis']['intro_copy']}
                - 초반 3초 영상 구성: {input_data['video_analysis']['intro_structure']}
                - 나레이션: {input_data['video_analysis']['narration']}
                - 음악: {input_data['video_analysis']['music']}
                - 폰트: {input_data['video_analysis']['font']}
                
                벤치마킹할 새로운 주제: {input_data['content_info']['topic']}
                
                위 릴스의 장점과 특징을 분석한 후, 새로운 주제에 맞게 벤치마킹하여 구체적인 스크립트, 캡션, 영상 기획을 제시해주세요.
                """
            }
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0,
            max_tokens=10000
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        st.error(f"분석 중 오류 발생: {str(e)}")
        return f"분석 중 오류 발생: {str(e)}"

def display_analysis_results(results, reels_info):
    st.markdown("""
        <style>
        .benchmark-analysis-title {
            font-size: 2.2rem;
            font-weight: 700;
            color: #405DE6;
            text-align: center;
            margin: 2.5rem auto;
            padding: 1rem 0;
            border-bottom: 3px solid #405DE6;
            width: 100%;
            background: linear-gradient(to right, transparent, #F0F2FF, transparent);
        }
        </style>
    """, unsafe_allow_html=True)

    # 1. 릴스 정보
    st.markdown('<div class="benchmark-analysis-title">📊 분석 결과</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="subsection-title">📱 릴스 정보</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="info-title">📌 기본 정보</div>', unsafe_allow_html=True)
        st.write(f"- 🗓️ 업로드 날짜: {reels_info['date']}")
        st.markdown(f"- 👤 계정: <a href='https://www.instagram.com/{reels_info['owner']}' target='_blank'>@{reels_info['owner']}</a>", unsafe_allow_html=True)
        st.write(f"- ⏱️ 영상 길이: {reels_info['video_duration']:.1f}초")
    
    with col2:
        st.markdown('<div class="info-title">📈 시청 반응</div>', unsafe_allow_html=True)
        st.write(f"- 👀 조회수: {format(reels_info['view_count'], ',')}회")
        st.write(f"- ❤️ 좋아요: {format(reels_info['likes'], ',')}개")
        st.write(f"- 💬 댓글: {format(reels_info['comments'], ',')}개")
    
    # 2. 스크립트와 캡션
    st.markdown('<div class="subsection-title">📝 콘텐츠 내용</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="info-title">🎙️ 스크립트</div>', unsafe_allow_html=True)
        st.write(reels_info["refined_transcript"])
    with col2:
        st.markdown('<div class="info-title">✍️ 캡션</div>', unsafe_allow_html=True)
        st.write(reels_info["caption"])
    
    # 3. GPT 분석 결과
    st.markdown('<div class="benchmark-analysis-title">🤖 벤치마킹 템플릿 분석</div>', unsafe_allow_html=True)
    
    # 벤치마킹 기획 섹션을 분리
    analysis_parts = results.split("# 6. 벤치마킹 적용 기획:")
    main_analysis = analysis_parts[0]  # 메인 분석 부분
    
    # GPT 분석 결과를 마크다운으로 변환하여 이모티콘 추가
    analysis_text = main_analysis.replace("# 1. 주제:", "# 🎯 1. 주제:")
    analysis_text = analysis_text.replace("# 2. 초반 3초", "# ⚡ 2. 초반 3초")
    analysis_text = analysis_text.replace("## 카피라이팅 :", "## ✍️ 카피라이팅 :")
    analysis_text = analysis_text.replace("## 영상 구성 :", "## 🎬 영상 구성 :")
    analysis_text = analysis_text.replace("# 3. 내용 구성:", "# 📋 3. 내용 구성:")
    analysis_text = analysis_text.replace("# 4. 개선할 점:", "# 🔍 4. 개선할 점:")
    analysis_text = analysis_text.replace("# 5. 적용할 점:", "# ✨ 5. 적용할 점:")
    
    # 메인 분석 결과 표시
    st.markdown(analysis_text)
    
    # 벤치마킹 기획 섹션 표시 (있는 경우에만)
    if len(analysis_parts) > 1:
        st.markdown('<div class="benchmark-analysis-title">📝 벤치마킹 기획</div>', unsafe_allow_html=True)
        planning_section = analysis_parts[1].strip()
        st.markdown(planning_section)

def display_progress():
    st.markdown("""
        <style>
        /* 프로그레스 바 스타일 */
        .stProgress > div > div > div {
            background-color: #E8F0FE !important;
        }
        /* 진행되지 않은 부분 스타일 */
        .stProgress > div > div {
            background-color: #E8F0FE !important;
        }
        .progress-label {
            text-align: center;
            color: #1c1c1e;
            font-weight: 600;
            margin-bottom: 10px;
            font-size: 1.1rem;
        }
        .step-container {
            margin: 20px 0;
            padding: 0 20%;  /* 프로그레스 바 너비 조절 */
        }
        </style>
    """, unsafe_allow_html=True)
    return st.empty()

@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_analysis(url, input_data):
    try:
        progress_placeholder = display_progress()
        start_time = time.time()
        
        def update_progress(current_time):
            progress = min(int((current_time - start_time) / 10) * 10, 100)  # 10초마다 10%씩 증가
            status = "🔄 분석 진행 중..." if progress < 100 else "✨ 분석 완료!"
            progress_placeholder.markdown(f"""
                <div class="step-container">
                    <div class="progress-label">{status}</div>
                </div>
            """, unsafe_allow_html=True)
            progress_placeholder.progress(progress)
            return progress
        
        # 주기적으로 진행 상태 업데이트
        while True:
            current_time = time.time()
            progress = update_progress(current_time)
            if progress >= 100:
                break
            time.sleep(1)  # 1초마다 업데이트
            
        # 메인 처리 로직
        video_path = download_video(url)
        if not video_path:
            st.error("영상 다운로드에 실패했습니다. URL을 확인해주세요.")
            return None
        
        reels_info = extract_reels_info(url, input_data['video_analysis'])
        if isinstance(reels_info, str):
            st.error(f"정보 추출 실패: {reels_info}")
            return None
        
        analysis = analyze_with_gpt4(reels_info, input_data)
        if "error" in analysis:
            st.error(f"AI 분석 실패: {analysis['error']}")
            return None
        
        # 완료 표시
        progress_placeholder.markdown("""
            <div class="step-container">
                <div class="progress-label">✨ 분석 완료!</div>
            </div>
        """, unsafe_allow_html=True)
        progress_placeholder.progress(100)
        time.sleep(1)
        progress_placeholder.empty()
        
        return {
            "analysis": analysis,
            "reels_info": reels_info
        }
        
    except Exception as e:
        st.error(f"처리 중 오류가 발생했습니다: {str(e)}")
        return None

def create_login_form():
    with st.form("instagram_login"):
        st.write("### Instagram 로그인")
        username = st.text_input("사용자명", type="default")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")
        
        if submitted:
            if username and password:
                # 로그인 성공 여부 확인
                try:
                    ydl_opts = {
                        'username': username,
                        'password': password,
                        'quiet': True,  # 불필요한 출력 숨김
                    }
                    # 로그인 정보만 저장하고 실제 테스트는 하지 않음
                    return {"username": username, "password": password}
                except Exception as e:
                    st.error(f"로그인 실패: {str(e)}")
                    return None
            else:
                st.error("사용자명과 비밀번호를 입력해주세요.")
                return None
    return None

def process_url(input_data, username, password):
    url = input_data.get("url", "")
    if not url:
        st.warning("URL을 입력해주세요.")
        return None
        
    # URL 유효성 검사
    if not is_valid_instagram_url(url):
        st.error("올바른 Instagram URL을 입력해주세요.")
        return None
    
    # 비디오 URL 가져오기 (로그인 정보 전달)
    video_url = get_video_url(url, username, password)
    if video_url:
        # 비디오 표시
        st.video(video_url)
        
        # 릴스 정보 추출
        reels_info = extract_reels_info(url, username=username, password=password)
        if isinstance(reels_info, str) and reels_info.startswith("Error"):
            st.error(reels_info)
            return None
            
        if reels_info:
            return {
                "url": url,
                "video_analysis": {
                    "intro_copy": st.session_state.form_data['video_intro_copy'],
                    "intro_structure": st.session_state.form_data['video_intro_structure'],
                    "narration": st.session_state.form_data['narration'],
                    "music": st.session_state.form_data['music'],
                    "font": st.session_state.form_data['font']
                },
                "content_info": {
                    "topic": input_data.get("content_info", {}).get("topic", "")
                }
            }
    else:
        st.error("Instagram URL에서 동영상을 찾을 수 없습니다.")
    
    return None

def main():
    st.title("✨ 릴스 벤치마킹 스튜디오")
    
    # 로그인 처리
    if "instagram_credentials" not in st.session_state:
        credentials = create_login_form()
        if credentials:
            st.session_state.instagram_credentials = credentials
            st.rerun()
    
    # 로그인된 경우에만 메인 기능 표시
    if "instagram_credentials" in st.session_state:
        input_data = create_input_form()
        if input_data:
            result = process_url(input_data, 
                               st.session_state.instagram_credentials["username"],
                               st.session_state.instagram_credentials["password"])
            if result:
                display_results(result)

if __name__ == "__main__":
    main() 