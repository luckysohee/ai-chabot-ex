import streamlit as st
import time

# -----------------------------
# API KEY
# -----------------------------
api_key = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]

if not api_key:
    st.error("API KEY 없음 (st.secrets에 GEMINI_API_KEY 추가 필요)")
    st.stop()

# -----------------------------
# Gemini client
# -----------------------------
from google import genai
from google.genai import types, errors

client = genai.Client(api_key=api_key)

config = types.GenerateContentConfig(
    max_output_tokens=1500,
    response_mime_type='text/plain',
    temperature=0.3,
    system_instruction='''
너는 생활체육지도자 + 필라테스 강사 + 영양사 + 식품영양학 교수다.
말투는 까칠하지만 핵심은 정확하고 실용적으로.

[절대 규칙]
- 음식 입력되면 반드시 운동 처방 포함
- 답변 구조 반드시 유지
- 칼로리는 추정이면 "추정" 표시
- 위험하면 안전 주의 1줄

[프로필 활용 규칙]
- 키/몸무게/나이/성별 기반 BMR/TDEE 추정
- BMI 위험범위면 운동강도 조절 언급

[답변 구조]
1) 한줄평
2) 섭취 요약
3) 칼로리/영양 + BMR/TDEE 추정
4) 운동 처방 A/B/C + 목표 소모칼로리
5) 다음 끼니 가이드 2개
6) 질문 1개
'''
)

# -----------------------------
# 프로필 상태
# -----------------------------
if "profile" not in st.session_state:
    st.session_state.profile = {
        "height": 165,
        "weight": 60.0,
        "age": 30,
        "sex": "여",
        "goal": "유지",
        "steps": 0
    }

# -----------------------------
# 프로필 텍스트 생성
# -----------------------------
def profile_text(p):
    return f"""
사용자 프로필
- 키: {p['height']} cm
- 몸무게: {p['weight']} kg
- 나이: {p['age']}
- 성별: {p['sex']}
- 목표: {p['goal']}
- 평소 걸음수: {p['steps']}
"""

# -----------------------------
# AI 호출 함수 (fallback 포함)
# -----------------------------
def get_ai_response(question, intensity, profile):

    prompt = f"""
{profile_text(profile)}

사용자 입력 음식:
{question}

운동 강도: {intensity}
"""

    models = [
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-3-flash-preview"
    ]

    last_error = None

    for model in models:
        for _ in range(2):
            try:
                res = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config
                )
                return res.text
            except errors.ServerError as e:
                last_error = e
                time.sleep(1)
            except Exception as e:
                last_error = e
                break

    return f"서버 오류. 잠시 후 다시 시도.\n에러:{last_error}"


# -----------------------------
# UI
# -----------------------------
st.set_page_config(
    page_title="AI 먹털교수",
    page_icon="🍎"
)

col1, col2 = st.columns([1.2,4.8])

with col1:
    st.markdown("## 🍎")

with col2:
    st.title("칼로리 청산일지")
    st.caption("먹은 음식 입력하면 운동 처방까지 추천함")
    st.markdown("---")

# -----------------------------
# 프로필 입력 UI
# -----------------------------
with st.expander("내 신체정보 입력", expanded=True):

    p = st.session_state.profile

    c1,c2,c3 = st.columns(3)
    with c1:
        p["height"] = st.number_input("키(cm)",120,220,p["height"])
    with c2:
        p["weight"] = st.number_input("몸무게(kg)",30.0,200.0,p["weight"])
    with c3:
        p["age"] = st.number_input("나이",10,100,p["age"])

    c4,c5,c6 = st.columns(3)
    with c4:
        p["sex"] = st.selectbox("성별",["여","남","비공개"])
    with c5:
        p["goal"] = st.selectbox("목표",["감량","유지","증량"])
    with c6:
        p["steps"] = st.number_input("평소 걸음수",0,50000,p["steps"])

    st.session_state.profile = p

# -----------------------------
# 채팅 기록
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role":"assistant","content":"먹은거 입력해."}
    ]

for m in st.session_state.messages:
    st.chat_message(m["role"]).write(m["content"])

# -----------------------------
# 운동 강도 선택
# -----------------------------
intensity = st.radio(
    "운동 강도",
    ["약","보통","강"],
    index=1,
    horizontal=True
)

# -----------------------------
# 입력창
# -----------------------------
question = st.chat_input("먹은 음식 입력")

if question:
    st.session_state.messages.append({"role":"user","content":question})
    st.chat_message("user").write(question)

    with st.spinner("분석중..."):
        reply = get_ai_response(question,intensity,st.session_state.profile)

    st.session_state.messages.append({"role":"assistant","content":reply})
    st.chat_message("assistant").write(reply)