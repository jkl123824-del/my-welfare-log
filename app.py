import streamlit as st
import google.generativeai as genai

# 1. 페이지 기본 설정 (모바일 최적화)
st.set_page_config(
    page_title="요양원 실습일지 생성기",
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 커스텀 CSS
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
st.caption("시간대를 직접 선택하고 간단한 키워드만 적어 실습일지를 작성하세요.")

# 2. API 키 설정 (Secrets 자동 불러오기 + 수동 입력 지원)
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key 입력", type="password")

if not api_key:
    st.info("👈 왼쪽 사이드바에 Gemini API Key를 입력해 주세요.")
    st.stop()

genai.configure(api_key=api_key)

# 3. 기본 정보 설정
with st.expander("📌 기본 정보 설정", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        student_name = st.text_input("실습생 이름", value="실습생")
        work_date = st.date_input("실습 날짜")
    with col2:
        supervisor_name = st.text_input("지도자 이름", value="지도자")
        time_range = st.text_input("근무 시간", value="09:00 ~ 18:00")

st.divider()

# 4. 동적 시간대 및 활동 입력 섹션
st.subheader("⏰ 활동 내역 작성")

if "activity_count" not in st.session_state:
    st.session_state.activity_count = 3

time_options = [
    "09:00 ~ 10:00",
    "10:00 ~ 11:00",
    "11:00 ~ 12:00",
    "12:00 ~ 13:00",
    "13:00 ~ 14:00",
    "14:00 ~ 15:00",
    "15:00 ~ 16:00",
    "16:00 ~ 17:00",
    "17:00 ~ 18:00",
    "직접 입력"
]

activities_data = []

preset_keywords = ["환경정리 및 위생", "인지재활 보조", "식사 수발", "케어록 작성", "말벗 서비스", "산책 및 이동보조"]
st.write("💡 **추천 활동 키워드:** " + ", ".join(preset_keywords))
st.write("")

for idx in range(st.session_state.activity_count):
    with st.container():
        st.markdown(f"**활동 {idx + 1}**")
        
        selected_time = st.selectbox(f"시간대 선택 #{idx + 1}", time_options, key=f"time_select_{idx}")
        
        if selected_time == "직접 입력":
            final_time = st.text_input(f"시간대 직접 입력 #{idx + 1}", placeholder="예: 09:30 ~ 10:30", key=f"time_custom_{idx}")
        else:
            final_time = selected_time

        act_name = st.text_input(f"활동명 #{idx + 1}", key=f"name_{idx}", placeholder="예: 인지재활 프로그램 보조")
        act_detail = st.text_area(f"간단한 내용 메모 #{idx + 1}", key=f"detail_{idx}", placeholder="예: 어르신 퍼즐 맞추기 보조, 집중력 저하 관찰함", height=70)
        
        if act_name or act_detail:
            activities_data.append({
                "time": final_time,
                "title": act_name,
                "memo": act_detail
            })
        st.markdown("---")

col_add, col_del = st.columns(2)
with col_add:
    if st.button("➕ 활동 칸 추가하기"):
        st.session_state.activity_count += 1
        st.rerun()
with col_del:
    if st.session_state.activity_count > 1:
        if st.button("➖ 마지막 칸 삭제하기"):
            st.session_state.activity_count -= 1
            st.rerun()

# 5. AI 생성 프롬프트 수정 (한 문장 생성 전용)
def generate_log(data):
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    당신은 노인복지시설(요양원) 사회복지 현장실습일지를 작성하는 전문 에이전트입니다.
    입력된 데이터(시간대, 활동명, 메모)를 바탕으로 각 시간대별 [활동 내용 및 방법]을 작성해 주세요.

    [작성 규칙 - 필수 준수]
    1. 각 시간대마다 '활동한 내용', '관찰한 사항', '배운 점'이 완벽히 어우러진 **단 한 문장**으로만 작성하세요.
    2. 항목을 불릿(•)으로 나누지 말고, '~(하)였으며, ~를 관찰하였고, ~를 배움.' 형태로 하나의 매끄러운 문장으로 구성하세요.
    3. 문장 끝은 개조식인 '~함', '~를 배움' 등으로 매끄럽게 마무리하세요.

    [입력 데이터]
    {data}

    [출력 양식 예시]
    ■ 활동 내용 및 방법

    [09:00 ~ 10:00] 센터위생 및 환경정리
    • 출근 후 환경 정돈과 아침 회의에 참여하여 당일 일정과 전체 업무 흐름을 공유받았으며, 이를 통해 체계적인 일과 준비가 어르신들의 쾌적한 일상에 미치는 중요성을 배움.

    [10:00 ~ 11:00] 인지재활 프로그램 보조
    • 어르신들의 칠교놀이 및 퍼즐 맞추기 활동을 보조하며 소근육 활용 정도를 관찰하였고, 개별 수행 능력에 맞춘 칭찬과 격려가 어르신의 참여 성취감을 높인다는 점을 배움.

    ■ 실습생 총평
    (오늘 실습 전체를 종합하는 2~3문장의 깔끔한 소감)
    """
    
    response = model.generate_model_content(prompt) if hasattr(model, 'generate_model_content') else model.generate_content(prompt)
    return response.text

# 6. 생성 결과 표시
st.write("")
if st.button("🚀 실습일지 문장 생성하기", type="primary"):
    if not activities_data:
        st.warning("최소 하나 이상의 활동 정보를 입력해 주세요!")
    else:
        with st.spinner("활동, 관찰, 배운 점을 한 문장으로 다듬는 중입니다..."):
            try:
                result = generate_log(activities_data)
                st.success("작성이 완료되었습니다!")
                st.subheader("📄 생성 결과")
                st.code(result, language=None)
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
