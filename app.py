import streamlit as st
import google.generativeai as genai
import json
import re
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

# 커스텀 CSS (모바일 자동 줄바꿈 & 화면 잘림 완전 방지)
st.markdown("""
    <style>
    /* 전체 여백 조절 */
    .main .block-container {
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        max-width: 100% !important;
    }
    
    /* 모바일 맞춤 버튼 디자인 */
    .stButton>button {
        width: 100% !important;
        border-radius: 6px !important;
        min-height: 2.5em !important;
        height: auto !important;
        font-weight: bold !important;
        padding: 4px 6px !important;
        font-size: 13px !important;
        white-space: normal !important;
        word-break: keep-all !important;
        line-height: 1.2 !important;
    }
    
    /* 입력창 글자 크기 모바일 최적화 */
    .stTextArea textarea {
        font-size: 15px !important;
    }
    
    /* HTML 커스텀 버튼 컨테이너 (자동 줄바꿈 플렉스박스) */
    .kw-container {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 5px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📝 실습일지")
st.caption("각 활동을 클릭하여 작성하세요. 시간을 변경하면 다음 활동 시간이 자동으로 연결됩니다.")

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

# 시간 자동 파싱 함수
def get_next_time_range(prev_time_str):
    try:
        times = re.findall(r'\d{1,2}:\d{2}', prev_time_str)
        if len(times) >= 2:
            end_time = times[1]
            h, m = map(int, end_time.split(':'))
            next_h = (h + 1) % 24
            next_end_str = f"{next_h:02d}:{m:02d}"
            return f"{end_time} ~ {next_end_str}"
    except Exception:
        pass
    return "10:00 ~ 11:00"

# 4. 카테고리별 추천 키워드 사전
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

default_time_slots = ["09:00 ~ 10:00", "10:00 ~ 11:00", "11:00 ~ 12:00", "13:00 ~ 14:00", "14:00 ~ 15:00", "15:00 ~ 16:00", "16:00 ~ 17:00", "17:00 ~ 18:00"]

# 5. 활동 내역 작성 섹션
st.subheader("⏰ 활동 내역 작성")

activities_data = []
v = st.session_state.reset_version
last_calculated_time = ""

for idx in range(st.session_state.activity_count):
    saved_name = st.session_state.draft_data.get(f"name_{idx}", "")
    saved_detail = st.session_state.draft_data.get(f"detail_{idx}", "")
    
    if idx == 0:
        default_t = default_time_slots[0]
    else:
        default_t = get_next_time_range(last_calculated_time) if last_calculated_time else default_time_slots[min(idx, len(default_time_slots)-1)]
        
    saved_time = st.session_state.draft_data.get(f"time_{idx}", default_t)

    if saved_name or saved_detail:
        status_label = f"✅ 활동 {idx + 1} ({saved_time}) - [{saved_name if saved_name else '메모 작성됨'}]"
    else:
        status_label = f"⚪ 활동 {idx + 1} ({saved_time}) - [미작성]"

    with st.expander(status_label, expanded=False):
        final_time = st.text_input(
            f"시간대 (수정 가능) #{idx + 1}", 
            value=saved_time, 
            key=f"time_custom_{v}_{idx}"
        )
        last_calculated_time = final_time

        act_name = st.text_input(
            f"활동명 #{idx + 1}", 
            value=saved_name, 
            key=f"name_{v}_{idx}", 
            placeholder="예: 출근 및 청소, 라운딩 및 말벗 등"
        )
        
        # --- 추천 키워드 영역 (스마트폰 크기에 맞춰 자동 줄바꿈) ---
        with st.container():
            st.caption("💡 추천 키워드 누르면 메모에 자동 입력")
            selected_cat = st.selectbox(f"카테고리 선택 #{idx+1}", list(KEYWORD_CATEGORIES.keys()), key=f"cat_{v}_{idx}")
            
            kw_list = KEYWORD_CATEGORIES[selected_cat]
            
            # 모바일 화면 폭에 맞춰 자동으로 배치되고 줄바꿈되는 3열
            kw_cols = st.columns(3)
            for k_i, kw in enumerate(kw_list):
                with kw_cols[k_i % 3]:
                    if st.button(kw, key=f"kw_btn_{v}_{idx}_{selected_cat}_{k_i}"):
                        current_val = st.session_state.get(f"detail_{v}_{idx}", saved_detail)
                        new_val = f"{current_val}, {kw}" if current_val else kw
                        st.session_state[f"detail_{v}_{idx}"] = new_val
                        st.rerun()

        act_detail = st.text_area(
            f"간단한 내용 메모 #{idx + 1}", 
            value=saved_detail, 
            key=f"detail_{v}_{idx}", 
            placeholder="특이사항이나 기억나는 어르신 반응, 배운 점을 메모해 보세요.", 
            height=70
        )
        
        st.session_state.draft_data[f"time_{idx}"] = final_time
        st.session_state.draft_data[f"name_{idx}"] = act_name
        st.session_state.draft_data[f"detail_{idx}"] = act_detail

        if act_name or act_detail:
            activities_data.append({
                "time": final_time,
                "title": act_name,
                "memo": act_detail
            })

# 제어 버튼 모음 (1줄 3개 모바일 완벽 대응)
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

# 6. AI 생성 프롬프트
def generate_log(data):
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    당신은 노인복지시설(요양원)에서 현장실습을 하는 사회복지 전공 실습생입니다.
    아래 [입력 데이터]를 바탕으로 예시 양식과 완전히 동일한 스타일로 실습일지를 완성해 주세요.

    [작성 양식 및 규칙 - 필수 준수]
    1. 제목 구성: "시간대 (활동명)" 형태로 서두를 시작하세요. (예: 09:00 ~ 10:00 (출근 및 청소))
    2. 본문 문단 구성: 각 시간대별로 [내가 직접 한 일/목적 ➔ 현장 관찰 사항 및 어르신 반응 ➔ 실습생으로서 느낀 점 및 배운 점]을 자연스럽게 2~3문장의 하나의 문단으로 작성하세요.
    3. 어조: 너무 딱딱하거나 연구원 같은 문체 대신, 현장에서 배우며 성찰하는 솔직하고 진정성 있는 '실습생 어조'(~하였다, ~를 알게 되었다, ~를 배웠다)를 유지하세요.
    4. 실습생의견: 입력된 당일 전체 활동을 종합하여 [오늘 가장 인상 깊었던 일 ➔ 이를 통해 깨달은 사회복지 실천 배움 ➔ 아쉬웠던 점 및 다음 실습에서의 다짐]이 포함된 1개의 정성스러운 문단으로 작성하세요.

    [입력 데이터]
    {data}

    [출력 양식 예시 - 아래 양식 그대로 출력할 것]
    활동 내용 및 방법

    09:00 ~ 10:00 (출근 및 청소)
    출근 후 어르신들의 생활실을 청소하고 환기를 진행하였다. 침구와 바닥을 정리하며 위생 관리에 신경 썼는데, 특히 감염 예방과 쾌적한 생활환경 조성을 위해 청결 유지가 중요하다는 점을 염두에 두고 작업하였다. 이를 통해 단순한 청소 업무도 어르신의 건강과 직결되는 사회복지사의 중요한 역할임을 알게 되었다.

    10:00 ~ 12:00 (오전 프로그램 보조)
    오전 실버 레크리에이션인 풍선 배구 진행을 보조하였다. 어르신들이 적극적으로 참여하실 수 있도록 박수를 유도하고 호응해 드렸는데, 처음엔 소극적이셨던 몇몇 어르신들도 점차 웃으며 참여하시는 모습을 볼 수 있었다. 이를 통해 여가 프로그램이 단순한 오락을 넘어 어르신들의 정서적 자극과 활력에도 중요한 역할을 한다는 것을 알게 되었다.

    실습생의견
    오늘 가장 인상 깊었던 일은 라운딩 중 어르신과 나눈 대화였다. 짧은 시간이었지만 어르신께서 밝은 표정으로 이야기를 이어가시는 모습을 보며 경청이 가진 힘을 새삼 느낄 수 있었다. 사회복지 실천에서 특별한 개입 없이도 진심으로 들어주는 태도만으로 라포형성이 이루어질 수 있다는 것을 배웠다. 한편으로는 아직 어르신들의 특성을 다 파악하지 못해 아쉬웠으며, 다음 실습에서는 어르신들의 개별 특성을 미리 숙지하여 더 자연스럽게 다가갈 수 있도록 노력해야겠다.
    """
    
    response = model.generate_model_content(prompt) if hasattr(model, 'generate_model_content') else model.generate_content(prompt)
    return response.text

# 7. 생성 결과 표시
st.write("")
if st.button("🚀 실습일지 문장 생성하기", type="primary"):
    if not activities_data:
        st.warning("최소 하나 이상의 활동 정보를 입력해 주세요!")
    else:
        with st.spinner("작성해주신 양식 스타일에 맞춰 실습일지를 정성껏 완성하는 중입니다..."):
            try:
                result = generate_log(activities_data)
                st.success("작성이 완료되었습니다!")
                st.subheader("📄 생성 결과")
                st.code(result, language=None)
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
