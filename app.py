import json
import streamlit as st
import google.generativeai as genai
from streamlit_local_storage import LocalStorage

# -----------------------------------------------------------------------------
# 1. 페이지 설정 및 초기화
# -----------------------------------------------------------------------------
st.set_page_config(page_title="📝 실습일지", layout="wide")
st.title("📝 실습일지")

local_store = LocalStorage()

# Gemini API 설정 (Streamlit Secrets에서 가져옴)
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("⚠️ GEMINI_API_KEY가 Secrets에 설정되어 있지 않습니다. .streamlit/secrets.toml 파일을 확인해 주세요.")

# -----------------------------------------------------------------------------
# 2. 상비 데이터 및 옵션 정의
# -----------------------------------------------------------------------------
# 기본 09:00 ~ 18:00 일과 템플릿
DEFAULT_SCHEDULES = [
    {"time": "09:00 ~ 10:00", "act_select": "환경정리 및 위생관리", "act_custom": "", "memo": ""},
    {"time": "10:00 ~ 11:30", "act_select": "오전 프로그램 보조", "act_custom": "", "memo": ""},
    {"time": "11:30 ~ 13:00", "act_select": "점심 식사 지원", "act_custom": "", "memo": ""},
    {"time": "13:00 ~ 14:00", "act_select": "휴게 및 오후 준비", "act_custom": "", "memo": ""},
    {"time": "14:00 ~ 15:30", "act_select": "라운딩 및 개별 상담·말벗", "act_custom": "", "memo": ""},
    {"time": "15:30 ~ 16:30", "act_select": "오후 프로그램 / 행정업무", "act_custom": "", "memo": ""},
    {"time": "16:30 ~ 17:30", "act_select": "저녁 식사 준비 및 마무리", "act_custom": "", "memo": ""},
    {"time": "17:30 ~ 18:00", "act_select": "일과 정리 및 피드백", "act_custom": "", "memo": ""},
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
# 3. Session State 및 LocalStorage 동기화
# -----------------------------------------------------------------------------
if "schedules" not in st.session_state:
    st.session_state["schedules"] = DEFAULT_SCHEDULES

if "active_memo_idx" not in st.session_state:
    st.session_state["active_memo_idx"] = 0

# 복원용 로직
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
# 4. 상단 컨트롤 버튼 (저장, 비우기, 템플릿 리셋)
# -----------------------------------------------------------------------------
st.subheader("⚙️ 일지 설정 및 데이터 관리")

col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1.5])

with col_btn1:
    if st.button("💾 임시 저장", use_container_width=True):
        # 현재 화면에 입력된 데이터 추출 및 저장
        save_list = []
        for idx in range(len(st.session_state["schedules"])):
            t_val = st.session_state.get(f"time_{idx}", "09:00 ~ 10:00")
            sel_val = st.session_state.get(f"act_select_{idx}", "✏️ 직접 입력")
            cus_val = st.session_state.get(f"act_custom_{idx}", "")
            mem_val = st.session_state.get(f"memo_{idx}", "")
            save_list.append({"time": t_val, "act_select": sel_val, "act_custom": cus_val, "memo": mem_val})
        
        local_store.setItem("my_welfare_log_data", json.dumps(save_list, ensure_ascii=False))
        st.toast("브라우저에 데이터가 임시 저장되었습니다!", icon="💾")

with col_btn2:
    if st.button("🗑️ 전체 비우기", use_container_width=True):
        local_store.removeItem("my_welfare_log_data")
        st.session_state["schedules"] = DEFAULT_SCHEDULES
        st.session_state.pop("restored_flag", None)
        st.toast("저장된 데이터가 비워졌습니다.", icon="🗑️")
        st.rerun()

with col_btn3:
    if st.button("🔄 기본 09:00~18:00 일과 불러오기", use_container_width=True):
        st.session_state["schedules"] = DEFAULT_SCHEDULES
        st.rerun()

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. 시간대별 활동 및 관찰 메모 입력 폼
# -----------------------------------------------------------------------------
st.subheader("⏰ 시간대별 일과 및 메모 입력")

current_schedules = st.session_state["schedules"]
updated_schedules = []

for idx, item in enumerate(current_schedules):
    with st.expander(f"📍 [{item.get('time', '시간 미정')}] {item.get('act_select', '')}", expanded=True):
        c1, c2, c3, c4 = st.columns([2, 2.5, 4.5, 1])
        
        with c1:
            time_val = st.text_input("시간대", value=item.get("time", ""), key=f"time_{idx}")
        
        with c2:
            current_act = item.get("act_select", "✏️ 직접 입력")
            act_idx = ACTIVITY_OPTIONS.index(current_act) if current_act in ACTIVITY_OPTIONS else 9
            
            act_select_val = st.selectbox("활동명 선택", options=ACTIVITY_OPTIONS, index=act_idx, key=f"act_select_{idx}")
            
            act_custom_val = ""
            if act_select_val == "✏️ 직접 입력":
                act_custom_val = st.text_input("활동명 직접 입력", value=item.get("act_custom", ""), key=f"act_custom_{idx}")
        
        with c3:
            memo_val = st.text_area(f"관찰 및 수행 메모", value=item.get("memo", ""), height=80, key=f"memo_{idx}")
            if st.button(f"📌 이 위치에 키워드 삽입 지정", key=f"focus_{idx}"):
                st.session_state["active_memo_idx"] = idx
                st.toast(f"#{idx+1}번 메모 입력창이 키워드 삽입 대상으로 지정되었습니다.")
        
        with c4:
            st.write("")
            st.write("")
            if st.button("❌ 삭제", key=f"del_{idx}"):
                st.session_state["schedules"].pop(idx)
                st.rerun()
        
        updated_schedules.append({
            "time": time_val,
            "act_select": act_select_val,
            "act_custom": act_custom_val,
            "memo": memo_val
        })

if st.button("➕ 시간대 추가", use_container_width=True):
    st.session_state["schedules"].append({"time": "18:00 ~ 19:00", "act_select": "✏️ 직접 입력", "act_custom": "", "memo": ""})
    st.rerun()

st.markdown("---")

# -----------------------------------------------------------------------------
# 6. 추천 키워드 자동 삽입 영역
# -----------------------------------------------------------------------------
st.subheader("💡 카테고리별 추천 키워드 (클릭 시 선택된 메모에 자동 입력)")
st.caption(f"현재 키워드가 입력될 대상: **#{st.session_state['active_memo_idx'] + 1}번 시간대 메모창**")

for cat_name, kw_list in KEYWORDS_BY_CATEGORY.items():
    st.write(f"**{cat_name}**")
    cols = st.columns(len(kw_list))
    for i, kw in enumerate(kw_list):
        with cols[i]:
            if st.button(kw, key=f"kw_{cat_name}_{i}"):
                target_idx = st.session_state["active_memo_idx"]
                current_text = st.session_state.get(f"memo_{target_idx}", "")
                new_text = f"{current_text}, {kw}" if current_text else kw
                st.session_state[f"memo_{target_idx}"] = new_text
                st.session_state["schedules"][target_idx]["memo"] = new_text
                st.rerun()

st.markdown("---")

# -----------------------------------------------------------------------------
# 7. AI 실습일지 생성 영역
# -----------------------------------------------------------------------------
st.subheader("🤖 Gemini AI 실습일지 생성")

if st.button("🚀 실습일지 작성 시작", type="primary", use_container_width=True):
    # 입력 데이터 통합 정리
    prompt_context = []
    for idx, item in enumerate(updated_schedules):
        final_act = item["act_custom"] if item["act_select"] == "✏️ 직접 입력" else item["act_select"]
        prompt_context.append(f"- 시간대: {item['time']} | 활동명: {final_act} | 관찰/수행 내용: {item['memo']}")
    
    full_schedule_str = "\n".join(prompt_context)
    
    system_prompt = f"""
당신은 요양원에서 사회복지 실습을 진행 중인 진정성 있고 솔직한 실습생입니다.
아래 제공된 시간대별 일과 및 메모를 바탕으로 정교한 '사회복지 실습일지'를 작성해 주세요.

[실습 내용]
{full_schedule_str}

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

    with st.spinner("AI가 실습일지를 다듬어 작성하고 있습니다..."):
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(system_prompt)
            
            st.success("✨ 실습일지가 생성되었습니다!")
            st.markdown("### 📝 생성된 실습일지")
            st.text_area("결과 복사용", value=response.text, height=500)
            st.markdown(response.text)
            
        except Exception as e:
            st.error(f"일지 생성 중 오류가 발생했습니다: {str(e)}")
