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
    </style>
""", unsafe_allow_html=True)

st.title("📝 실습일지")
st.caption("다양한 키워드 버튼을 눌러 20일간 다채로운 실습일지를 작성해 보세요.")

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

# 4. 카테고리별 전체 키워드 데이터 사전 (제시해주신 키워드 전체 세분화 반영)
KEYWORD_CATEGORIES = {
    "🧹 환경/위생": [
        "생활실 청소", "침구 정리", "환기", "소독 및 방역", 
        "배식 준비", "식당 정리", "물품 정리", "세탁물 정리", "욕실 청결 점검"
    ],
    "🤝 일상지원(ADL)": [
        "식사보조", "배설보조", "이동보조(휠체어)", "세면/목욕 보조", 
        "옷 갈아입히기 보조", "체위변경 보조", "낙상예방 활동"
    ],
    "🎨 여가/프로그램": [
        "실버 레크리에이션 보조", "인지활동(색칠/퍼즐) 보조", "음악치료 보조", 
        "원예활동 보조", "미술활동 보조", "체조/운동 보조", "생신잔치/행사 보조"
    ],
    "💬 라운딩/정서": [
        "말벗 활동", "개별 라운딩", "어르신 욕구 파악", "정서적 지지", 
        "경청", "가족 면회 지원", "임종 돌봄 참관"
    ],
    "📖 사정/상담/기록": [
        "초기면접 참관", "욕구사정 참관", "개별 상담 참관", 
        "사례관리 회의 참관", "상담일지 작성 보조", "케이스 기록 열람"
    ],
    "📑 행정/사무": [
        "서류 정리", "입소/퇴소 서류 보조", "프로그램 계획서 작성 보조", 
        "회의록 작성", "통계자료 정리", "각종 신청서 작성 보조"
    ],
    "🏫 교육/회의/협력": [
        "직원회의 참관", "사례회의 참관", "신입 오리엔테이션 참여", 
        "다학제 회의 참관", "외부 기관 방문/연계"
    ],
    "💡 관찰/배운점 용어": [
        "라포형성", "욕구사정", "자기결정권", "임파워먼트(역량강화)", 
        "클라이언트 중심 접근", "사례관리", "사회복지실천기술", "비밀보장", 
        "아웃리치", "다학제 협업", "인권감수성", "옹호(애드보커시)"
    ]
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
        
        # --- 키워드 선택 영역 ---
        with st.expander(f"💡 활동 #{idx + 1} 추천 키워드 선택해서 메모에 넣기"):
            selected_cat = st.selectbox(f"카테고리 선택 #{idx+1}", list(KEYWORD_CATEGORIES.keys()), key=f"cat_{v}_{idx}")
            st.caption("원하는 단어를 클릭하면 아래 메모 칸에 자동으로 추가됩니다:")
            
            # 버튼들을 3열로 배치
            kw_list = KEYWORD_CATEGORIES[selected_cat]
            kw_cols = st.columns(3)
            for k_i, kw in enumerate(kw_list):
                with kw_cols[k_i % 3]:
                    if st.button(kw, key=f"kw_btn_{v}_{idx}_{selected_cat}_{k_i}"):
                        current_val = st.session_state.get(f"detail_{v}_{idx}", saved_detail)
                        new_val = f"{current_val}, {kw}" if current_val else kw
                        st.session_state[f"detail_{v}_{idx}"] = new_val
                        st.rerun()

        act_detail = st.text_area(f"간단한 내용 메모 #{idx + 1}", value=saved_detail, key=f"detail_{v}_{idx}", placeholder="위 키워드 버튼을 누르거나 생각나는 내용을 자유롭게 적으세요.", height=70)
        
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
                window.parent.localStorage realm.removeItem('{STORAGE_KEY}');
                window.parent.location.reload();
            </script>
            """,
            height=0
        )

# 6. AI 생성 프롬프트 (실습생다운 솔직하고 자연스러운 톤앤매너로 교정)
def generate_log(data):
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    당신은 노인복지시설(요양원)에서 현장실습을 하고 있는 '사회복지 전공 실습생'입니다.
    입력된 데이터(시간대, 활동명, 메모/키워드)를 바탕으로 각 시간대별 [활동 내용 및 방법]을 솔직하고 정성스러운 실습생 어조로 작성해 주세요.

    [작성 어조 및 톤앤매너 - 필수 준수]
    1. 너무 학술적이거나 거창한 전문가(연구원/시설장) 어조를 피하고, **현장에서 직접 배우고 깨닫는 실습생의 솔직한 시선**으로 작성하세요.
    2. 전문용어(예: 자기결정권, 라포형성 등)는 한 문장에 과도하게 남발하지 말고, **자연스럽게 1개 정도만 녹여내어** 실습생다운 진정성을 살리세요.
    3. 각 시간대마다 '내가 직접 수행한 일', '어르신이나 현장을 관찰한 점', '이를 통해 배운 솔직한 점'이 매끄럽게 어우러진 **단 한 문장**으로 작성하세요.
    4. 불릿(•)이나 항목을 나누지 말고, '~(하)였으며, ~를 관찰하였고, ~를 배움.' 형태로 하나의 매끄러운 문장으로 구성하세요.
    5. 문장 끝은 개조식인 '~함', '~를 배움', '~를 알게 됨' 등으로 자연스럽게 마무리하세요.

    [입력 데이터]
    {data}

    [출력 양식 예시]
    ■ 활동 내용 및 방법

    [09:00 ~ 10:00] 센터위생 및 환경정리
    • 아침 출근 후 생활실 환기와 소독을 도우며 하루 일과를 준비하였고, 쾌적한 환경 조성이 어르신들의 건강과 직결된다는 점을 배움.

    [10:00 ~ 11:00] 인지재활 프로그램 보조
    • 어르신들의 퍼즐 맞추기 활동을 곁에서 보조하며 완성할 수 있도록 응원해 드렸고, 어르신의 속도에 맞추어 기다려 드리는 것이 소통의 기본임을 알게 됨.

    ■ 실습생 총평
    (오늘 실습 전체를 경험하며 느낀 점과 배운 점을 솔직하게 담은 2~3문장의 총평)
    """
    
    response = model.generate_model_content(prompt) if hasattr(model, 'generate_model_content') else model.generate_content(prompt)
    return response.text

# 7. 생성 결과 표시
st.write("")
if st.button("🚀 실습일지 문장 생성하기", type="primary"):
    if not activities_data:
        st.warning("최소 하나 이상의 활동 정보를 입력해 주세요!")
    else:
        with st.spinner("실습생의 시선으로 정성스럽게 문장을 다듬는 중입니다..."):
            try:
                result = generate_log(activities_data)
                st.success("작성이 완료되었습니다!")
                st.subheader("📄 생성 결과")
                st.code(result, language=None)
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
