import streamlit as st
if "GEMINI_API_KEY" in st.secrets:
    api_key=st.secrets["GEMINI_API_KEY"]

from google import genai

client=genai.Client(api_key=api_key)

from google.genai import types
config=types.GenerateContentConfig(
    max_output_tokens=10000,
    response_mime_type='text/plain',
    system_instruction='너는 생활체육지도자 자격증+ 필라테스 자격증+ 영양사 자격증+ 식품영양학 교수님이야. 까칠하고 매우 차갑지만, 가끔 츤데레로 인간미를 갖춘 센스있는 여성임',
    temperature=0.3
)  

def get_ai_response(question):
    response=client._models.generate_content(
        model=""gemini-3-flash-preview",
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
    st.markdown(
        """
        <h1>먹은만큼 운동하자</h1>
        <p>이 챗봇은 먹은만큼 칼로리 계산 및 운동 방법을 명쾌하게 제안합니다. </p>
        """,
        unsafe_allow_html=True
    )

    for msg in st.session_state.messages:
        st.chat_message(msg['role']).write(msg['content'])
    
    question=st.chat_input('시간별로 섭취 음식을 입력하세요.')
    if question:
        question=question.replace('\n','  \n')
        st.session_state.messages.append({'role':'user','content':question})
        st.chat_message('user').write(question)

        with st. spinner('응답 작성 중'):
            response=get_ai_response(question)
            st.session_state.messages.append({'role':'assistant','content':response})
            st.chat_message('assistant').write(response)