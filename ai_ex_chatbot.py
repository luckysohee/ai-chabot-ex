import streamlit as st
if "GEMINI_API_KEY" in st.secrets:
    api_key=st.secrets["GEMINI_API_KEY"]

from google import genai

client=genai.Client(api_key=api_key)

from google.genai import types
config=types.GenerateContentConfig(
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

    [답변 구조 - 항상 이 순서]
    1) 한줄평(까칠하게 1문장)
    2) 섭취 요약(음식 목록 1~3줄)
    3) 칼로리/대략 영양(추정치 범위로)
    4) 운동 처방(필수)
     - A안: 집에서 20~30분(유산소+근력+코어) : 세트/횟수/시간까지 구체적으로
     - B안: 헬스장 40~60분(가능하면)
     - C안: 필라테스/스트레칭 10분(회복/부담 적게)
     - '오늘 목표 소모 칼로리'를 대략 제시
    5) 다음 끼니/간식 가이드(현실적인 대안 2개)
    6) 추가 질문(딱 1개만): 예) "오늘 활동량(걷기 시간) 어느 정도야?"
'''
)  

def get_ai_response(question):
    prompt = f"""
    사용자 입력(먹은 것):
    {question}

    요구사항:
    - 반드시 운동 처방 A/B/C안을 포함해서 답변할 것.
    - 위에서 정의한 '답변 구조'를 그대로 지킬 것.
    """
    response=client._models.generate_content(
        model="gemini-3-flash-preview",
        contents=question,
        config=config
    )
    return response.text
#------------------------------------------

st.set_page_config(
    page_title="AI 먹운교수",
    page_icon='./logo/가운소녀.png'
)

col1, col2=st.columns([1.2,4.8])

with col1:
    st.image("./logo/가운소녀.png",width=200)

with col2:
    st.markdown(
        """
        <h1>먹은만큼 운동하자</h1>
        <p>이 챗봇은 먹은만큼 칼로리 계산 및 운동 방법을 제안합니다. </p>
        """,
        unsafe_allow_html=True
    )
    st.markdown("---")

    if "messages" not in st.session_state:
        st.session_state.messages=[
            {'role':'assistant','content':'먹은거 다 적어봐라. 그만큼 털어보자!'}
        ]

    for msg in st.session_state.messages:
        st.chat_message(msg['role']).write(msg['content'])

    intensity = st.radio(
        "운동 강도 선택",
        ["약", "보통", "강"],
        index=1,
        horizontal=True
    )
    
    question=st.chat_input('시간별로 섭취 음식을 입력하세요.')
    if question:
        question=question.replace('\n','  \n')
        st.session_state.messages.append({'role':'user','content':question})
        st.chat_message('user').write(question)

        with st. spinner('응답 작성 중'):
            response=get_ai_response(question,intensity)
            st.session_state.messages.append({'role':'assistant','content':response})
            st.chat_message('assistant').write(response)