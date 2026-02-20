import json
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    st.stop()

client = genai.Client(api_key=api_key)



# -----------------------------
def calc_kcal(food_text: str) -> dict:
    """
    아주 단순한 예시 DB. 너 서비스에 맞게 계속 확장하면 됨.
    """
    DB = {
        "공기밥": 300, "밥": 300,
        "라면": 500,
        "치킨": 1200,
        "피자": 900,
        "계란": 75, "삶은계란": 75,
        "바나나": 105,
        "아보카도": 240,
        "우유": 130,
        "요거트": 150,
        "치즈": 110,
        "아메리카노": 5, "커피": 5,
        "맥주": 150, "소주": 400,
    }

    matched = []
    total = 0
    text = food_text.replace(" ", "")

    for k, v in DB.items():
        if k.replace(" ", "") in text:
            matched.append({"item": k, "kcal": v})
            total += v

    return {
        "total_kcal_est": total,
        "matched_items": matched,
        "note": "간단 DB 기반 추정(정확도는 음식/양 정보에 따라 달라짐)"
    }


# -----------------------------

# -----------------------------
calc_kcal_decl = types.FunctionDeclaration(
    name="calc_kcal",
    description="사용자 식사 텍스트에서 대략 칼로리를 추정해 반환한다.",
    parameters_json_schema={
        "type": "object",
        "properties": {
            "food_text": {"type": "string", "description": "사용자가 먹은 음식 텍스트"}
        },
        "required": ["food_text"]
    },
)
tool = types.Tool(function_declarations=[calc_kcal_decl])

config_fc = types.GenerateContentConfig(
    temperature=0.0,

    tool_config=types.ToolConfig(
        function_calling_config=types.FunctionCallingConfig(mode="ANY")
    ),

    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    tools=[tool],
    response_mime_type="text/plain",
    system_instruction="""
너는 칼로리 계산을 먼저 해야 한다.
반드시 tool(calc_kcal)만 호출해라. 자연어 답변 금지.
"""
)


# -----------------------------

# -----------------------------
class WorkoutPlan(BaseModel):
    A_home_20_30min: str = Field(description="집에서 20~30분 플랜(유산소+근력+코어), 세트/횟수/시간 포함")
    B_gym_40_60min: str = Field(description="헬스장 40~60분 플랜(가능하면)")
    C_pilates_stretch_10min: str = Field(description="필라테스/스트레칭 10분 플랜(회복용)")

class CoachJSON(BaseModel):
    one_line: str = Field(description="까칠한 한줄평 1문장")
    intake_summary: List[str] = Field(description="섭취 요약 음식 리스트(1~3줄)")
    kcal_estimate: Dict[str, Any] = Field(description="칼로리 추정 결과(총합/근거/주의)")
    workout_plan: WorkoutPlan
    target_burn_kcal: int = Field(description="오늘 목표 소모 칼로리(대략 정수)")
    next_meal_guides: List[str] = Field(description="다음 끼니/간식 가이드 2개")
    followup_question: str = Field(description="추가 질문 1개")

config_json = types.GenerateContentConfig(
    temperature=0.3,
    max_output_tokens=2000,
    response_mime_type="application/json",
    response_schema=CoachJSON,
    system_instruction="""
너는 생활체육지도자 + 필라테스 강사 + 영양사 + 식품영양학 교수다.
말투는 까칠하지만, 핵심은 정확하고 실용적이어야 한다.

규칙:
- 반드시 운동 처방을 포함해라(A/B/C).
- 칼로리/영양은 추정이면 '추정'이라고 명시해라.
- 마지막에 질문은 딱 1개만.
- 출력은 무조건 JSON만. (설명 문장, 마크다운, 코드블록 금지)
"""
)


# -----------------------------

# -----------------------------
def get_ai_response(question: str, intensity: str = "보통") -> dict:

    fc_prompt = f"""
사용자 입력(먹은 것):
{question}
"""
    resp_fc = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=fc_prompt,
        config=config_fc
    )

    if not resp_fc.function_calls:
        # mode="ANY"면 거의 없겠지만, 혹시 대비
        tool_result = {"total_kcal_est": 0, "matched_items": [], "note": "tool call 실패(예외 케이스)"}
    else:
        call = resp_fc.function_calls[0]
        # 모델이 calc_kcal 호출하도록 강제했으니 이름 체크
        if call.name != "calc_kcal":
            tool_result = {"total_kcal_est": 0, "matched_items": [], "note": f"예상치 못한 함수 호출: {call.name}"}
        else:
            tool_result = calc_kcal(**call.args)


    json_prompt = f"""
사용자 입력(먹은 것): {question}
운동 강도: {intensity}

[칼로리 계산 결과(tool)]
{json.dumps(tool_result, ensure_ascii=False)}

요구사항:
- A/B/C 운동 처방을 구체적으로(세트/횟수/시간 포함)
- target_burn_kcal는 운동 강도에 맞게 조정(약<보통<강)
"""
    resp_json = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=json_prompt,
        config=config_json
    )

    # resp_json.text 는 JSON 문자열
    try:
        return json.loads(resp_json.text)
    except Exception:
        # 혹시라도 깨지면 원문을 감싸서 반환
        return {"error": "JSON 파싱 실패", "raw": resp_json.text, "tool_result": tool_result}


# ------------------------------------------

# ------------------------------------------
st.set_page_config(
    page_title="AI 먹털교수",
    page_icon="./logo/가운소녀.png"
)

col1, col2 = st.columns([1.2, 4.8])

with col1:
    st.image("./logo/가운소녀.png", width=200)

with col2:
    st.markdown(
        """
        <h1>칼로리 청산일지</h1>
        <p>이 챗봇은 식단 계산 및 운동 방법을 제안합니다.</p>
        """,
        unsafe_allow_html=True
    )
    st.markdown("---")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "먹은거 다 적어라. 털어보자!", "intake_summary": [], "kcal_estimate": {}, "workout_plan": {"A_home_20_30min": "", "B_gym_40_60min": "", "C_pilates_stretch_10min": ""}, "target_burn_kcal": 0, "next_meal_guides": [], "followup_question": ""}
        ]

    # 대화 출력(assistant는 JSON으로 보여주기)
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant" and isinstance(msg["content"], dict):
                st.json(msg["content"])
            else:
                st.write(msg["content"])

    intensity = st.radio("운동 강도 선택", ["약", "보통", "강"], index=1, horizontal=True)

    question = st.chat_input("섭취 음식을 입력하세요.")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        with st.spinner("응답 작성 중"):
            response_json = get_ai_response(question, intensity)
            st.session_state.messages.append({"role": "assistant", "content": response_json})
            with st.chat_message("assistant"):
                st.json(response_json)