import json
import streamlit as st
import google.generativeai as genai
from streamlit_local_storage import LocalStorage

# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 Gemini API 초기화
# -----------------------------------------------------------------------------
st.set_page_config(page_title="📝 실습일지", layout="wide")
st.title("📝 실습일지")

local_store = LocalStorage()

try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("⚠️ Secrets에 GEMINI_API_KEY 설정이 안 되어 있습니다.")

# -----------------------------------------------------------------------------
# 2. 기본 데이터 정의
# -----------------------------------------------------------------------------
DEFAULT_SCHEDULES = [
    {"time": "09:00 ~ 10:00", "act_select": "환경정리 및 위생관리", "act_custom": "", "memo": ""},
    {"time": "10:00 ~ 11:30", "act_select": "오전 프로그램 보조", "act_custom": "", "memo": ""},
    {"time": "11:30 ~ 13:00", "act_select": "점심 식사 지원", "act_custom": "", "memo": ""},
    {"time": "13:00 ~ 14:00", "act_select": "휴게 및 오후 준비", "act_custom": "", "memo": ""},
    {"time": "14:00 ~ 15:30", "act_select": "라운딩 및 개별 상담·말벗", "act_custom": "", "memo": ""},
    {"time": "15:30 ~ 16:30", "act_select": "오후 프로그램 / 행정업무", "act_custom": "", "memo": ""},
    {"time": "16:30 ~ 17:30", "act_select": "저녁 식사 준비 및 마무리", "act_custom": "", "memo": ""},
    {"time": "17:30 ~ 18:00", "act_select": "일과 정리 및 피드백", "act_custom": "", "memo": ""}
]

ACTIVITY_OPTIONS = [
    "출근 및 인수인계",
    "환경정리 및 위생관리",
    "오전 프로그램 보조",
    "점심 식사 지원",
    "휴게 및 오후 준비",
    "라운딩 및 개별 상담·말벗",
    "오후 프로그램 / 행정업무",
    "저녁 식사 준비 및 마무리",
    "일과 정리 및 피드백",
    "✏️ 직접 입력"
]

KEYWORDS_BY_CATEGORY = {
    "🧹 환경/위생": ["생활실 환기", "침구류 정리", "바닥 청소", "소독 조치", "물품 정돈"],
    "🍲 ADL 지원": ["식사보조", "저작곤란 관찰", "구강위생 관리", "체위변경", "이동보조"],
    "🎨 여가/프로그램": ["인지활동(색칠)", "건강체조", "음악치료", "원예활동", "참여 유도"],
    "💬 라운딩/정서": ["말벗 지원", "정서적 경청", "상태 파악", "표정 및 행동 관찰"],
    "📋 사정/상담": ["초기면접 참관", "욕구사정 참관", "사례관리 참관", "상담일지 작성"],
    "📁 행정/교육": ["케이스 기록", "서류 정리", "슈퍼바이저 피드백", "OT 및 시설 교육"]
}

# -----------------------------------------------------------------------------
# 3. Session State 초기화 및 복원
# -----------------------------------------------------------------------------
if "schedules" not in st.session_state:
    st.session_state["schedules"] = DEFAULT_SCHEDULES

if "active_idx" not in st.session_state:
    st.session_state["active_idx"] = 0

# LocalStorage 데이터 복원
restored_data = local_store.getItem("my_welfare_log_data")
if restored_data and "restored_flag" not in st.session_state:
    try:
        parsed = json.loads(restored_data)
        if isinstance(parsed, list) and len(parsed) > 0:
            st.session_state["schedules"] = parsed
            st.session_state["restored_flag"] = True
    except Exception:
        pass

# -----------------------------------------------------------------------------
# 4. 상단 버튼 모음 (임시저장, 비우기, 리셋)
# -----------------------------------------------------------------------------
c_btn1, c_btn2, c_btn3 = st.columns([1, 1, 1.5])

with c_btn1:
    if st.button("💾 임시 저장", use_container_width=True):
        local_store.setItem("my_welfare_log_data", json.dumps(st.session_state["schedules"], ensure_ascii=False))
        st.toast("저장되었습니다!", icon="💾")

with c_btn2:
    if st.button("🗑️ 전체 비우기", use_container_width=True):
        local_store.removeItem("my_welfare_log_data")
        st.session_state["schedules"] = DEFAULT_SCHEDULES
        st.session_state.pop("restored_flag", None)
        st.session_state["active_idx"] = 0
        st.toast("전체 비우기 완료", icon="🗑️")
        st.rerun()

with c_btn3:
    if st.button("🔄 기본 시간대 템플릿 불러오기", use_container_width=True):
        st.session_state["schedules"] = DEFAULT_SCHEDULES
        st.session_state["active_idx"] = 0
        st.rerun()

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. 시간대별 목록 작성 영역 (심플화)
# -----------------------------------------------------------------------------
st.subheader("⏰ 시간대별 일과 작성")

# 인덱스 초과 방지 안전장치
if st.session_state["active_idx"] >= len(st.session_state["schedules"]):
    st.session_state["active_idx"] = max(0, len(st.session_state["schedules"]) - 1)

for idx, item in enumerate(st.session_state["schedules"]):
    is_active = (idx == st.session_state["active_idx"])
    
    # 선택된 항목은 시각적으로 표기
    bg_mark = "📌 " if is_active else ""
    st.markdown(f"##### {bg_mark}시간대 #{idx+1}")
    
    col1, col2, col3, col4 = st.columns([2, 2.5, 4.5, 1])
    
    with col1:
        # 시간대 입력
        new_time = st.text_input("시간대", value=item["time"], key=f"t_{idx}")
        st.session_state["schedules"][idx]["time"] = new_time
        
    with col2:
        # 활동명 선택
        cur_act = item["act_select"]
        act_i = ACTIVITY_OPTIONS.index(cur_act) if cur_act in ACTIVITY_OPTIONS else 9
        
        new_act = st.selectbox("활동명", options=ACTIVITY_OPTIONS, index=act_i, key=f"s_{idx}")
        st.session_state["schedules"][idx]["act_select"] = new_act
        
        if new_act == "✏️ 직접 입력":
            new_cus = st.text_input("직접 입력", value=item["act_custom"], key=f"c_{idx}")
            st.session_state["schedules"][idx]["act_custom"] = new_cus
            
    with col3:
        # 관찰 메모 입력
        new_memo = st.text_area("관찰/수행 메모", value=item["memo"], height=70, key=f"m_{idx}")
        st.session_state["schedules"][idx]["memo"] = new_memo
        
        if st.button(f"🎯 키워드 넣을 칸으로 지정", key=f"set_active_{idx}"):
            st.session_state["active_idx"] = idx
            st.rerun()
            
    with col4:
        st.write("")
        st.write("")
        if st.button("❌", key=f"del_{idx}"):
            st.session_state["schedules"].pop(idx)
            st.rerun()

col_add1, col_add2 = st.columns([1, 4])
with col_add1:
    if st.button("➕ 시간대 추가", use_container_width=True):
        st.session_state["schedules"].append({"time": "18:00 ~ 19:00", "act_select": "✏️ 직접 입력", "act_custom": "", "memo": ""})
        st.rerun()

st.markdown("---")

# -----------------------------------------------------------------------------
# 6. 추천 키워드 영역
# -----------------------------------------------------------------------------
active_target_num = st.session_state["active_idx"] + 1
st.subheader("💡 추천 키워드")
st.info(f"현재 키워드를 클릭하면 **#{active_target_num}번 메모 칸**에 추가됩니다. (다른 칸에 넣으려면 위에서 '🎯 키워드 넣을 칸으로 지정' 클릭)")

for cat_name, kw_list in KEYWORDS_BY_CATEGORY.items():
    st.write(f"**{cat_name}**")
    cols = st.columns(len(kw_list))
    for i, kw in enumerate(kw_list):
        with cols[i]:
            if st.button(kw, key=f"kw_{cat_name}_{i}"):
                cur_target = st.session_state["active_idx"]
                old_text = st.session_state["schedules"][cur_target]["memo"]
                
                if old_text:
                    st.session_state["schedules"][cur_target]["memo"] = f"{old_text}, {kw}"
                else:
                    st.session_state["schedules"][cur_target]["memo"] = kw
                st.rerun()

st.markdown("---")

# -----------------------------------------------------------------------------
# 7. Gemini AI 생성 영역
# -----------------------------------------------------------------------------
st.subheader("🤖 AI 실습일지 생성")

if st.button("🚀 실습일지 작성 시작", type="primary", use_container_width=True):
    prompt_context = []
    for item in st.session_state["schedules"]:
        act_name = item["act_custom"] if item["act_select"] == "✏️ 직접 입력" else item["act_select"]
        prompt_context.append(f"- 시간대: {item['time']} | 활동명: {act_name} | 메모: {item['memo']}")
    
    full_str = "\n".join(prompt_context)
    
    system_prompt = f"""
당신은 요양원에서 사회복지 실습을 진행 중인 진정성 있고 솔직한 실습생입니다.
아래 시간대별 메모를 바탕으로 정교한 '사회복지 실습일지'를 작성해 주세요.

[실습 내용]
{full_str}

[작성 지침 및 양식 요구사항]
1. 각 시간대 항목마다 반드시 아래의 3문단 구조로 상세히 작성할 것:
   - 시간대 및 활동명 (예: 09:00 ~ 10:00 (환경정리 및 위생관리))
   - [내가 한 일]: 내가 수행한 주요 보조 업무나 작업 내용
   - [관찰 사항]: 어르신들의 반응, 상태변화, 요양보호사/사회복지사 선생님들의 케어 방식
   - [느낀 점/배운 점]: 실습생으로서 깨달은 점, 사회복지적 의미, 배운 점
2. 어조: 솔직하고 진정성 있는 실습생 어조 (~하였다, ~를 알게 되었다, ~라 느꼈다).
3. 일지 가장 마지막 부분에는 반드시 [실습생의견 (총평)] 섹션을 추가하고 아래 3가지 내용을 포함할 것:
   - 오늘 가장 인상 깊었던 일
   - 깨달은 점
   - 아쉬운 점 및 다음 실습에서의 다짐
"""

    with st.spinner("AI가 일지를 작성 중입니다..."):
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(system_prompt)
            
            st.success("✨ 실습일지 작성 완료!")
            st.text_area("결과 복사용 (전체 선택 후 복사 가능)", value=response.text, height=400)
            st.markdown(response.text)
        except Exception as e:
            st.error(f"생성 중 오류 발생: {str(e)}")
