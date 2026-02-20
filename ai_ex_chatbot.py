import streamlit as st

# -----------------------------
# 0) API KEY
# -----------------------------
api_key = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]

from google import genai
client = genai.Client(api_key=api_key)

from google.genai import types
config = types.GenerateContentConfig(
    max_output_tokens=1500,
    response_mime_type='text/plain',
    temperature=0.3,
    system_instruction='''
    너는 생활체육지도자 + 필라테스 강사 + 영양사 + 식품영양학 교수다.
    말투는 까칠하고 차갑지만, 핵심은 정확하고 실용적으로 준다. 가끔 츤데레 한 줄 허용.

    [절대 규칙]
    - 사용자가 먹은 음식을 말하면, 잔소리만 하지 말고 반드시 '운동 처방'을 포함해 답한다.
    - 답변은 아래 구조를 무조건 지킨다. (항목 누락 금지)
    - 칼로리/영양은 추정치면 '추정'이라고 명시한다.
    - 의료/부상 위험이 있으면 안전 주의 한 줄 포함하고, 무리한 처방 금지.

    [추가 규칙 - 사용자 프로필 활용]
    - 사용자가 제공한 키/몸무게/나이/성별/활동량(있으면)을 바탕으로
      기초대사량(BMR)과 유지칼로리(TDEE)를 "추정"으로 계산해 제시하라.
    - 그 값으로 '오늘 목표 소모 칼로리'를 더 현실적으로 제시하라.
    - 과체중(BMI>=25 추정) 또는 저체중(BMI<18.5 추정)이면 안전/볼륨 조절을 1줄 언급하라.

    [답변 구조 - 항상 이 순서]
    1) 한줄평(까칠하게 1문장)
    2) 섭취 요약(음식 목록 1~3줄)
    3) 칼로리/대략 영양(추정치 범위로) + (가능하면) BMR/TDEE 추정치
    4) 운동 처방(필수)
     - A안: 집에서 20~30분(유산소+근력+코어) : 세트/횟수/시간까지 구체적으로
     - B안: 헬스장 40~60분(가능하면)
     - C안: 필라테스/스트레칭 10분(회복/부담 적게)
     - '오늘 목표 소모 칼로리'를 대략 제시
    5) 다음 끼니/간식 가이드(현실적인 대안 2개)
    6) 추가 질문(딱 1개만): 예) "오늘 활동량(걷기 시간) 어느 정도야?"
'''
)

# -----------------------------
# 1) 프로필(키/몸무게 등) 저장
# -----------------------------
def ensure_profile_state():
    if "profile" not in st.session_state:
        st.session_state.profile = {
            "height_cm": None,
            "weight_kg": None,
            "age": None,
            "sex": "여",  # 선택값
            "goal": "유지",
            "daily_steps": None,
        }

ensure_profile_state()

# -----------------------------
# 2) 프롬프트에 프로필 포함
# -----------------------------
def build_profile_text(profile: dict) -> str:
    parts = []
    if profile.get("height_cm"): parts.append(f"- 키: {profile['height_cm']} cm")
    if profile.get("weight_kg"): parts.append(f"- 몸무게: {profile['weight_kg']} kg")
    if profile.get("age"): parts.append(f"- 나이: {profile['age']} 세")
    if profile.get("sex"): parts.append(f"- 성별(선택): {profile['sex']}")
    if profile.get("goal"): parts.append(f"- 목표(선택): {profile['goal']}")
    if profile.get("daily_steps"): parts.append(f"- 평소 걸음수(선택): {profile['daily_steps']} 보/일")
    if not parts:
        return "사용자 프로필: (미제공)"
    return "사용자 프로필:\n" + "\n".join(parts)

def get_ai_response(question, intensity="보통", profile=None):
    profile_text = build_profile_text(profile or {})
    prompt = f"""
{profile_text}

사용자 입력(먹은 것):
{question}

운동 강도: {intensity}

요구사항:
- 반드시 운동 처방 A/B/C안을 포함해서 답변할 것.
- 위에서 정의한 '답변 구조'를 그대로 지킬 것.
- 프로필이 제공되었으면 BMR/TDEE를 '추정'으로 계산해 포함할 것.
"""
    response = client._models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
        config=config
    )
    return response.text

# ------------------------------------------
st.set_page_config(
    page_title="AI 먹털교수",
    page_icon='./logo/가운소녀.png'
)

col1, col2 = st.columns([1.2, 4.8])

with col1:
    st.image("./logo/가운소녀.png", width=200)

with col2:
    st.markdown(
        """
        <h1>칼로리 청산일지</h1>
        <p>이 챗봇은 식단 계산 및 운동 방법을 제안합니다. </p>
        """,
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ✅ 프로필 입력 UI (추가)
    with st.expander("내 프로필(키/몸무게) 입력", expanded=True):
        p = st.session_state.profile
        c1, c2, c3 = st.columns(3)
        with c1:
            p["height_cm"] = st.number_input("키(cm)", min_value=120, max_value=220, value=p["height_cm"] or 165, step=1)
        with c2:
            p["weight_kg"] = st.number_input("몸무게(kg)", min_value=30.0, max_value=200.0, value=float(p["weight_kg"] or 60.0), step=0.1)
        with c3:
            p["age"] = st.number_input("나이(선택)", min_value=10, max_value=100, value=int(p["age"] or 30), step=1)

        c4, c5, c6 = st.columns(3)
        with c4:
            p["sex"] = st.selectbox("성별(선택)", ["여", "남", "기타/비공개"], index=["여","남","기타/비공개"].index(p["sex"] or "여"))
        with c5:
            p["goal"] = st.selectbox("목표(선택)", ["감량", "유지", "증량"], index=["감량","유지","증량"].index(p["goal"] or "유지"))
        with c6:
            p["daily_steps"] = st.number_input("평소 걸음수(선택)", min_value=0, max_value=50000, value=int(p["daily_steps"] or 0), step=500)

        st.session_state.profile = p  # 저장

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {'role': 'assistant', 'content': '먹은거 다 적어라. 털어보자!'}
        ]

    for msg in st.session_state.messages:
        st.chat_message(msg['role']).write(msg['content'])

    intensity = st.radio(
        "운동 강도 선택",
        ["약", "보통", "강"],
        index=1,
        horizontal=True
    )

    question = st.chat_input('섭취 음식을 입력하세요.')
    if question:
        question = question.replace('\n', '  \n')
        st.session_state.messages.append({'role': 'user', 'content': question})
        st.chat_message('user').write(question)

        with st.spinner('응답 작성 중'):
            response = get_ai_response(question, intensity, st.session_state.profile)
            st.session_state.messages.append({'role': 'assistant', 'content': response})
            st.chat_message('assistant').write(response)