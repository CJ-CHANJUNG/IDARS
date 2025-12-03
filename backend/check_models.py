import google.generativeai as genai
# 기존 설정 파일에서 키 가져오기
try:
    from Config.api_config import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = "AIzaSyAlHsrJn2F5bnlHW_iMoSLvHG7GNosZ3OE"

genai.configure(api_key=GEMINI_API_KEY)

print("🔍 사용 가능한 모델 목록 조회 중...")
try:
    for m in genai.list_models():
        # 'generateContent' 기능(채팅/생성)이 가능한 모델만 출력
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"❌ 조회 실패: {e}")