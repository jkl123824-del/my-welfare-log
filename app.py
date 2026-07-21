import streamlit as st
import google.generativeai as genai
import json
from streamlit_local_storage import LocalStorage

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="실습일지",
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# LocalStorage 객체 생성
local_storage = LocalStorage()

# 커스텀 CSS (버튼 스타일 및 태그 최적화)
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
    .keyword-badge {
        display: inline-block;
        background-color: #e1f5fe;
        color: #0288d1;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 12px;
        margin-right: 4px;
        margin-bottom: 4px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📝 실습일지")
st.caption("키워드 버튼을 눌러 메모를 채우고 [💾 임시 저장]을 활용해 보세요.")

# 2. API 키 설정 (Secrets 자동 불러오기)
api_key = st.secrets.get("GEMINI_API_KEY") or st.sidebar.text_input("Gemini API Key 입력", type="password")

if not api_key:
    st.info("👈 왼쪽 사이드바에 Gemini API Key를 입력해 주세요.")
    st.stop()

genai.configure(api_key=api_key)

# 3. LocalStorage 및 세션 초기화
STORAGE_KEY = "welfare_log_draft_data"

if "reset_version" not in st.session_state:
    st.session_state.reset_version = 0

if "draft_loaded" not in st.session_state:
    st.session_state.draft_loaded = False
    st.session_state.draft_data = {}

# 브라우저 저장소 데이터 불러오기
if not st.session_state.draft_loaded:
    saved_json = local_storage.getItem(STORAGE_KEY)
    if saved_json:
        try:
            st.session_state.draft_data = json.loads(saved_json)
        except Exception:
            st.session_state.draft_data = {}
    st.session_state.draft_loaded = True

if "activity_count" not in st.session_state:
    st.session_state.activity_count = max(3, len([k for k in st.session_state.draft_data.keys() if k.startswith("name_")]))

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

# 4. 카테고리별 추천 키워드 데이터 사전
KEYWORD_CATEGORIES = {
    "🧹 환경/위생": ["생활실 청소", "침구 정리", "환기 및 소독", "배식 준비", "식당 정리", "물품/세탁물 정리"],
    "🤝 일상지원": ["식사보조", "배설보조", "이동보조(휠체어)", "세면/목욕 보조", "체위변경", "낙상예방"],
    "🎨 여가/프로그램": ["실버 레크리에이션", "인지활동(색칠/퍼즐)", "음악치료", "원예/미술활동", "체조/운동"],
    "💬 라운딩/정서": ["말벗 활동", "개별 라운딩", "어르신 욕구 파악", "정서적 지지", "가족 면회 지원"],
    "📖 사정/행정": ["초기면접 참관", "욕구사정 참관", "상담일지 작성", "사례회의 참관", "서류 정리"],
    "💡 관찰/전문용어": ["라포형성", "자기결정권 존중", "잔존능력 유지", "임파워먼트", "클라이언트 중심", "인권감수성"]
}

# 5. 활동 내역 작성 섹션
st.subheader("⏰ 활동 내역 작성")

activities_data = []
v = st.session_state.reset_version

for idx in range(st.session_state.activity_count):
    with st.container():
        st.markdown(f"**활동 {idx + 1}**")
        
        saved_time = st.session_state.draft_data.get(f"time_{idx}", time_options[min(idx, len(time_options)-2)])
        saved_name = st.session_state.draft_data.get(f"name_{idx}", "")
        saved_detail = st.session_state.draft_data.get(f"detail_{idx}", "")

        selected_time = st.selectbox(
            f"시간대 선택 #{idx + 1}", 
            time_options, 
            index=time_options.index(saved_time) if saved_time in time_options else len(time_options)-1, 
            key=f"time_select_{v}_{idx}"
        )
        
        if selected_time == "직접 입력":
            final_time = st.text_input(f"시간대 직접 입력 #{idx + 1}", value=saved_time if saved_time not in time_options else "", placeholder="예: 09:30 ~ 10:30", key=f"time_custom_{v}_{idx}")
        else:
            final_time = selected_time

        act_name = st.text_input(f"활동명 #{idx + 1}", value=saved_name, key=f"name_{v}_{idx}", placeholder="예: 인지재활 프로그램 보조")
        
        # --- 키워드 버튼 클릭 시 메모에 추가되는 익스팬더 ---
        with st.expander(f"💡 활동 #{idx + 1} 키워드 클릭해서 메모에 넣기"):
            selected_cat = st.radio(f"카테고리 선택 #{idx+1}", list(KEYWORD_CATEGORIES.keys()), horizontal=True, key=f"cat_{v}_{idx}")
            st.caption("원하는 단어를 누르면 아래 메모 칸에 자동으로 추가됩니다:")
            
            # 버튼들을 가로로 나열
            kw_cols = st.columns(3)
            for k_i, kw in enumerate(KEYWORD_CATEGORIES[selected_cat]):
                with kw_cols[k_i % 3]:
                    if st.button(kw, key=f"kw_btn_{v}_{idx}_{selected_cat}_{k_i}"):
                        current_val = st.session_state.get(f"detail_{v}_{idx}", saved_detail)
                        new_val = f"{current_val}, {kw}" if current_val else kw
                        st.session_state[f"detail_{v}_{idx}"] = new_val
                        st.rerun()

        act_detail = st.text_area(f"간단한 내용 메모 #{idx + 1}", value=saved_detail, key=f"detail_{v}_{idx}", placeholder="위 키워드 버튼을 누르거나 직접 메모를 적으세요.", height=70)
        
        # 실시간 상태 보존
        st.session_state.draft_data[f"time_{idx}"] = final_time
        st.session_state.draft_data[f"name_{idx}"] = act_name
        st.session_state.draft_data[f"detail_{idx}"] = act_detail

        if act_name or act_detail:
            activities_data.append({
                "time": final_time,
                "title": act_name,
                "memo": act_detail
            })
        st.markdown("---")

# 제어 버튼 모음
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("➕ 칸 추가"):
        st.session_state.activity_count += 1
        st.rerun()
with col2:
    if st.button("💾 임시 저장"):
        local_storage.setItem(STORAGE_KEY, json.dumps(st.session_state.draft_data))
        st.toast("스마트폰/PC 브라우저에 안전하게 저장되었습니다!", icon="✅")
with col3:
    if st.button("🗑️ 전체 비우기"):
        st.session_state.draft_data = {}
        st.session_state.activity_count = 3
        st.session_state.reset_version += 1
        
        st.components.v1.html(
            f"""
            <script>
                window.parent.localStorage.removeItem('{STORAGE_KEY}');
                window.parent.location.reload();
            </script>
            """,
            height=0
        )

# 6. AI 생성 프롬프트 (키워드를 학술적·실천적 사회복지 용어로 다듬는 지침 강화)
def generate_log(data):
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    당신은 노인복지시설(요양원) 사회복지 현장실습일지를 작성하는 전문 에이전트입니다.
    입력된 데이터(시간대, 활동명, 메모/키워드)를 바탕으로 각 시간대별 [활동 내용 및 방법]을 고급스러운 사회복지 전문 문장으로 작성해 주세요.

    [작성 규칙 - 필수 준수]
    1. 메모에 단어나 키워드(예: 식사보조, 라포형성, 자기결정권)만 나열되어 있더라도, 이를 매끄럽고 전문적인 '사회복지실천 문장'으로 발전시키세요.
    2. 각 시간대마다 '활동한 내용', '관찰한 사항', '배운 점(전문용어 포함)'이 완벽히 어우러진 **단 한 문장**으로만 작성하세요.
    3. 불릿(•)이나 항목을 나누지 말고, '~(하)였으며, ~를 관찰하였고, ~를 배움.' 형태로 하나의 매끄러운 문장으로 구성하세요.
    4. 문장 끝은 개조식인 '~함', '~를 배움' 등으로 매끄럽게 마무리하세요.

    [입력 데이터]
    {data}

    [출력 양식 예시]
    ■ 활동 내용 및 방법

    [09:00 ~ 10:00] 센터위생 및 환경정리
    • 출근 후 환경 정돈과 아침 회의에 참여하여 당일 일정과 전체 업무 흐름을 공유받았으며, 이를 통해 체계적인 일과 준비가 어르신들의 쾌적한 일상에 미치는 중요성을 배움.

    ■ 실습생 총평
    (오늘 실습 전체를 종합하는 2~3문장의 소감)
    """
    
    response = model.generate_model_content(prompt) if hasattr(model, 'generate_model_content') else model.generate_content(prompt)
    return response.text

# 7. 생성 결과 표시
st.write("")
if st.button("🚀 실습일지 문장 생성하기", type="primary"):
    if not activities_data:
        st.warning("최소 하나 이상의 활동 정보를 입력해 주세요!")
    else:
        with st.spinner("선택하신 키워드를 활용하여 전문 사회복지 실습문장을 다듬는 중입니다..."):
            try:
                result = generate_log(activities_data)
                st.success("작성이 완료되었습니다!")
                st.subheader("📄 생성 결과")
                st.code(result, language=None)
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
