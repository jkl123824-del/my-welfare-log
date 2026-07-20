import streamlit as st
import google.generativeai as genai

# 1. 페이지 기본 설정 (모바일 최적화)
st.set_page_config(
    page_title="요양원 실습일지 생성기",
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 커스텀 CSS (모바일 가독성 및 버튼 터치 영역 확대)
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    .stTextArea textarea {
        font-size: 16px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📝 요양원 실습일지 생성기")
st.caption("간단한 메모만 입력하면 짧고 명확한 일지 문장을 만들어 드립니다.")

# 2. API 키 설정
api_key = st.sidebar.text_input("Gemini API Key 입력", type="password")

if not api_key:
    st.info("👈 왼쪽 사이드바에 Gemini API Key를 입력해 주세요.")
    st.stop()

genai.configure(api_key=api_key)

# 3. 기본 설정 섹션
with st.expander("📌 기본 정보 설정", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        student_name = st.text_input("실습생 이름", value="실습생")
        work_date = st.date_input("실습 날짜")
    with col2:
        supervisor_name = st.text_input("지도자 이름", value="지도자")
        time_range = st.text_input("근무 시간", value="09:00 ~ 18:00")

st.divider()

# 4. 시간대별 활동 입력 섹션
st.subheader("⏰ 시간대별 활동 입력")

default_times = [
    "09:00 ~ 10:00",
    "10:00 ~ 11:30",
    "11:30 ~ 13:00",
    "13:00 ~ 15:00",
    "15:00 ~ 16:30",
    "16:30 ~ 18:00"
]

activities_data = []

preset_keywords = ["환경정리 및 위생", "인지재활 보조", "식사 수발", "케어록 작성", "말벗 서비스", "산책 및 이동보조"]
st.write("💡 **자주 쓰는 활동 키워드:** " + ", ".join(preset_keywords))

for idx, time_slot in enumerate(default_times):
    with st.container():
        st.markdown(f"**[{time_slot}]**")
        act_name = st.text_input(f"활동명", key=f"name_{idx}", placeholder="예: 센터위생 및 환경정리")
        act_detail = st.text_area(f"간단한 내용 메모", key=f"detail_{idx}", placeholder="예: 생활실 환기, 침상 소독 및 청소", height=70)
        
        if act_name or act_detail:
            activities_data.append({
                "time": time_slot,
                "title": act_name,
                "memo": act_detail
            })
        st.markdown("---")

# 5. AI 생성 로직
def generate_log(data):
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    당신은 노인복지시설(요양원) 사회복지 현장실습 일지 작성을 돕는 에이전트입니다.
    아래 입력된 메모를 바탕으로 실습일지 [활동 내용 및 방법]과 [실습생 의견]을 작성해주세요.

    [작성 수칙]
    1. 각 문장은 15~20자 내외로 매우 짧고 명확하게 작성하세요.
    2. 문말 어조는 '~함', '~을 배움', '~을 확인함'과 같은 명확한 개조식 문장으로 끝내세요.
    3. 군더더기 없는 단문 위주로 구성하세요.

    [입력 데이터]
    {data}

    [출력 형식]
    ■ 활동 내용 및 방법
    - [시간대] 활동명
      • 생성된 짧은 문장 1
      • 생성된 짧은 문장 2

    ■ 실습생 의견
    (3~4문장의 짧고 간결한 성찰 및 배운 점)
    """
    
    response = model.generate_content(prompt)
    return response.text

# 6. 생성 버튼 및 결과 출력
if st.button("🚀 실습일지 문장 생성하기", type="primary"):
    if not activities_data:
        st.warning("최소 하나 이상의 활동 내용을 입력해 주세요!")
    else:
        with st.spinner("짧고 명확한 문장으로 일지를 작성 중입니다..."):
            try:
                result = generate_log(activities_data)
                st.success("작성이 완료되었습니다!")
                st.subheader("📄 생성 결과")
                st.code(result, language=None)
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
