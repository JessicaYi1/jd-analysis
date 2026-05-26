import json
import os

import requests
import streamlit as st

JOBS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "jobs.json")

st.set_page_config(page_title="岗位智能分析看板 2.0", page_icon="📊", layout="wide")

# ═══════════════════════════════════════════
# 全局 CSS 美化
# ═══════════════════════════════════════════

st.markdown("""
<style>
/* ── 全局字体 & 变量 ── */
:root {
    --primary: #6366f1;
    --primary-light: #818cf8;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
    --bg: #f8fafc;
    --card-bg: #ffffff;
    --text: #1e293b;
    --text-secondary: #64748b;
    --border: #e2e8f0;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
    --shadow: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05);
    --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -4px rgba(0,0,0,0.04);
    --radius: 12px;
    --radius-sm: 8px;
}

html, body, [class*="st-"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ── 主背景 ── */
.stApp {
    background: linear-gradient(135deg, #f0f4ff 0%, #f8fafc 30%, #f0fdf4 70%, #fefce8 100%);
}

/* ── 顶部标题栏：仅改背景，不碰内部图标 ── */
[data-testid="stHeader"] {
    background: linear-gradient(135deg, #f0f4ff, #f8fafc);
}
/* 只美化我们自己的 h1 标题，避开 Streamlit 工具栏的图标 */
h1 {
    font-weight: 700 !important;
    font-size: 2rem !important;
    color: #4f46e5 !important;
}

/* ── 侧边栏 ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%) !important;
    border-right: none !important;
}
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] li {
    color: #e2e8ff !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #c7d2fe !important;
    font-weight: 700 !important;
}
/* 保留 side bar 内 alert 框的原始可读性 */
[data-testid="stSidebar"] .stAlert {
    color: inherit !important;
}
[data-testid="stSidebar"] .stAlert * {
    color: inherit !important;
}
[data-testid="stSidebar"] button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
[data-testid="stSidebar"] button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(99,102,241,0.4) !important;
}
[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    padding: 12px !important;
}
[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    color: #c7d2fe !important;
}
[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
    color: #94a3b8 !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.15) !important;
}

/* ── 卡片容器 ── */
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"]:hover {
    box-shadow: var(--shadow-lg);
}

/* ── 按钮 ── */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
    border: none !important;
    font-size: 13px !important;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
}
.stButton > button[kind="secondary"] {
    background: white !important;
    color: #6366f1 !important;
    border: 1.5px solid #6366f1 !important;
}
.stButton > button[kind="secondary"]:hover {
    background: #eef2ff !important;
}

/* ── 进度条 ── */
.stProgress > div > div {
    border-radius: 100px !important;
    height: 8px !important;
}
.stProgress > div > div > div {
    border-radius: 100px !important;
    background: linear-gradient(90deg, #6366f1, #8b5cf6) !important;
}

/* ── Metric ── */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #f0f4ff, #faf5ff);
    border-radius: 10px;
    padding: 16px;
    border: 1px solid #e0e7ff;
}
[data-testid="stMetricValue"] {
    font-weight: 700 !important;
    color: #6366f1 !important;
}

/* ── Alert 圆角 ── */
.stAlert {
    border-radius: 8px !important;
    border-left: 4px solid !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
}

/* ── Text Area ── */
textarea {
    border-radius: 8px !important;
    border: 1.5px solid #e2e8f0 !important;
}
textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.1) !important;
}

/* ── 技能标签 chips ── */
.skill-chip {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 100px;
    font-size: 13px;
    font-weight: 500;
    margin: 2px 4px;
}
.chip-purple { background: #ede9fe; color: #6d28d9; }
.chip-blue   { background: #dbeafe; color: #1d4ed8; }
.chip-green  { background: #d1fae5; color: #047857; }
.chip-amber  { background: #fef3c7; color: #b45309; }
.chip-rose   { background: #ffe4e6; color: #be123c; }
.chip-slate  { background: #f1f5f9; color: #475569; }

/* ── 渐变分隔线 ── */
hr.divider-gradient, .divider-gradient {
    height: 2px;
    border: none;
    background: linear-gradient(90deg, transparent, #c7d2fe, #a5b4fc, #c7d2fe, transparent);
    margin: 24px 0;
}

/* ── selectbox & multiselect ── */
[data-baseweb="select"] > div {
    border-radius: 8px !important;
}

/* ── 滚动条 ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #c7d2fe; border-radius: 100px; }
::-webkit-scrollbar-thumb:hover { background: #a5b4fc; }
</style>
""", unsafe_allow_html=True)

CATEGORIES = [
    "全部",
    "AI产品经理",
    "策略产品经理",
    "中后台产品经理",
    "通用PM/前台产品经理",
]

COLORS = {
    "AI产品经理": "#7c3aed",
    "策略产品经理": "#2563eb",
    "中后台产品经理": "#059669",
    "通用PM/前台产品经理": "#d97706",
}

BACKEND_URL = "http://127.0.0.1:8000"

# ═══════════════════════════════════════════
# API 调用函数
# ═══════════════════════════════════════════

def delete_job(job_id: str) -> bool:
    try:
        r = requests.delete(f"{BACKEND_URL}/jobs/{job_id}", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def analyze_jobs(job_ids: list[str]) -> dict | None:
    try:
        r = requests.post(
            f"{BACKEND_URL}/analyze_jobs",
            json={"job_ids": job_ids},
            timeout=120,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def parse_resume(resume_text: str) -> dict | None:
    try:
        r = requests.post(
            f"{BACKEND_URL}/parse_resume",
            json={"resume_text": resume_text},
            timeout=120,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def match_resume_job(job_id: str, resume_id: str = "") -> dict | None:
    try:
        r = requests.post(
            f"{BACKEND_URL}/match_resume_job",
            json={"job_id": job_id, "resume_id": resume_id},
            timeout=120,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def generate_rewrite(job_id: str, resume_id: str = "", project_name: str = "") -> dict | None:
    try:
        r = requests.post(
            f"{BACKEND_URL}/generate_resume_rewrite",
            json={
                "job_id": job_id,
                "resume_id": resume_id,
                "project_name": project_name or "JD智能分析与简历匹配系统",
            },
            timeout=120,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def generate_message(job_id: str, resume_id: str = "", match_report_id: str = "") -> dict | None:
    try:
        r = requests.post(
            f"{BACKEND_URL}/generate_application_message",
            json={
                "job_id": job_id,
                "resume_id": resume_id,
                "match_report_id": match_report_id,
            },
            timeout=120,
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def submit_feedback(target_type: str, target_id: str, feedback_type: str, comment: str = "") -> bool:
    try:
        r = requests.post(
            f"{BACKEND_URL}/submit_feedback",
            json={
                "target_type": target_type,
                "target_id": target_id,
                "feedback_type": feedback_type,
                "comment": comment,
            },
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def load_jobs() -> list[dict]:
    if not os.path.exists(JOBS_FILE):
        return []
    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


# ═══════════════════════════════════════════
# 初始化 session_state
# ═══════════════════════════════════════════

DEFAULTS = {
    "resume_profile": None,
    "resume_raw_text": "",
    "match_reports": {},   # job_id -> match_report
    "rewrite_reports": {},  # job_id -> rewrite_report
    "messages": {},         # job_id -> messages
    "compare_result": None,
}

for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ═══════════════════════════════════════════
# 主页面
# ═══════════════════════════════════════════

def main():
    st.title("📊 岗位智能分析看板 2.0")
    st.caption("数据来源：BOSS 直聘 → 浏览器书签采集 → LLM 自动分类 → 简历匹配评分")

    # ── 侧边栏 ──
    all_jobs_for_filter = load_jobs()
    all_cities = sorted({j.get("city", "") for j in all_jobs_for_filter if j.get("city")})
    all_companies = sorted({j.get("company", "") for j in all_jobs_for_filter if j.get("company")})

    with st.sidebar:
        st.header("🔍 筛选条件")
        selected_category = st.selectbox("细分方向", CATEGORIES, index=0)
        selected_city = st.selectbox("Base 地", ["全部"] + all_cities, index=0)
        selected_company = st.selectbox("公司", ["全部"] + all_companies, index=0)

        st.divider()
        st.caption("📌 使用方法")
        st.caption("1. 在 BOSS 直聘岗位详情页点击书签")
        st.caption("2. 数据自动发送至后端分析")
        st.caption("3. 在本页粘贴简历并解析")
        st.caption("4. 选择岗位生成匹配度分析")
        st.caption("5. 查看简历优化建议和投递话术")

        if st.button("🔄 手动刷新", use_container_width=True):
            st.rerun()

        job_count = len(load_jobs())
        st.metric("已收录岗位", job_count)

        # ── 简历状态指示 ──
        st.divider()
        if st.session_state["resume_profile"]:
            st.success("✅ 简历已解析")
            target = st.session_state["resume_profile"].get("target_role", "未知")
            st.caption(f"目标岗位：{target}")
        else:
            st.warning("⚠️ 尚未解析简历")

        # ── 岗位对比分析 ──
        st.divider()
        st.header("📊 岗位对比分析")

        all_jobs_raw = load_jobs()
        if all_jobs_raw:
            job_options = {
                f"[{j.get('company', '?')}] {j.get('jobName', '未知')}": j.get("id", "")
                for j in all_jobs_raw
            }
            selected_labels = st.multiselect(
                "选择岗位（可搜索）",
                options=list(job_options.keys()),
                placeholder="搜索岗位名或公司名...",
            )
            selected_ids = [job_options[label] for label in selected_labels]

            if st.button("🔍 开始分析", use_container_width=True, disabled=len(selected_ids) < 2):
                with st.spinner("正在综合分析所选岗位..."):
                    result = analyze_jobs(selected_ids)
                if result:
                    st.session_state["compare_result"] = result
                    st.rerun()
                else:
                    st.error("分析失败，请检查后端服务")
        else:
            st.caption("暂无岗位数据可供分析")

    # ── 主区域：对比分析结果 ──
    if st.session_state["compare_result"]:
        result = st.session_state["compare_result"]
        analysis = result.get("analysis", {})

        with st.container(border=True):
            rh1, rh2 = st.columns([4, 1])
            with rh1:
                st.subheader("📊 岗位对比分析报告")
                jobs_label = "、".join(
                    f"[{j['company']}] {j['jobName']}" for j in result.get("analyzed_jobs", [])
                )
                st.caption(f"分析岗位：{jobs_label}")
            with rh2:
                if st.button("✕ 关闭报告", use_container_width=True):
                    st.session_state["compare_result"] = None
                    st.rerun()
            st.divider()

            if analysis.get("summary"):
                st.info(analysis["summary"])

            must_have = analysis.get("must_have_skills", [])
            if must_have:
                st.markdown("### 🔴 必须技能")
                for s in must_have:
                    with st.expander(f"{s.get('skill', '')} （{s.get('frequency', '')}）", expanded=False):
                        st.markdown(f"**为什么必须**：{s.get('why', '')}")
                        st.markdown(f"**怎么学**：{s.get('how_to_learn', '')}")

            bonus = analysis.get("bonus_skills", [])
            if bonus:
                st.markdown("### 🟡 加分技能")
                for s in bonus:
                    with st.expander(f"{s.get('skill', '')} （{s.get('frequency', '')}）", expanded=False):
                        st.markdown(f"**为什么加分**：{s.get('why', '')}")
                        st.markdown(f"**怎么学**：{s.get('how_to_learn', '')}")

            ind = analysis.get("industry_knowledge", [])
            if ind:
                st.markdown("### 🏭 行业认知")
                for item in ind:
                    with st.expander(item.get("domain", ""), expanded=False):
                        st.markdown(f"**为什么需要**：{item.get('why', '')}")
                        st.markdown(f"**如何建立**：{item.get('how_to_build', '')}")

            proj = analysis.get("project_experience", [])
            if proj:
                st.markdown("### 🛠 项目实战建议")
                for p in proj:
                    diff = p.get("difficulty", "")
                    label = f"{'🔵' if '零基础' in diff else '🟣'} {p.get('project', '')}（{diff}）"
                    with st.expander(label, expanded=False):
                        st.markdown(f"**覆盖能力**：{p.get('skill_mapping', '')}")
                        st.markdown(f"**具体步骤**：{p.get('concrete_steps', '')}")

            thresholds = analysis.get("hard_thresholds", [])
            if thresholds:
                st.markdown("### ⚠️ 硬性门槛")
                for t in thresholds:
                    sev = t.get("severity", "")
                    icon = "🔴" if "卡死" in sev else ("🟡" if "筛选" in sev else "🟢")
                    with st.expander(f"{icon} {t.get('requirement', '')} — {sev}", expanded=False):
                        st.markdown(f"**破局方法**：{t.get('workaround', '')}")

            iv = analysis.get("interview_prep", [])
            if iv:
                st.markdown("### 🎯 面试准备")
                for item in iv:
                    with st.expander(item.get("direction", ""), expanded=False):
                        st.markdown(f"**典型问题**：{item.get('sample_question', '')}")
                        st.markdown(f"**答题思路**：{item.get('how_to_answer', '')}")

            path = analysis.get("learning_path", [])
            if path:
                st.markdown("### 📈 提升路线图")
                path_sorted = sorted(path, key=lambda x: x.get("phase", 0))
                for p in path_sorted:
                    st.markdown(
                        f"**阶段 {p.get('phase', '')}**：{p.get('focus', '')} "
                        f"（{p.get('duration', '')}）"
                    )
                    for a in p.get("actions", []):
                        st.markdown(f"- {a}")
                    st.markdown("")

        st.divider()

    # ═══════════════════════════════════════════
    # 2.0 新增：我的简历 Profile
    # ═══════════════════════════════════════════

    with st.container(border=True):
        st.header("📝 我的简历 Profile")

        if st.session_state["resume_profile"]:
            # 已解析过简历，展示结构化结果
            rp = st.session_state["resume_profile"]
            c1, c2 = st.columns([3, 1])
            with c1:
                # 教育背景
                edu = rp.get("education", {})
                if edu.get("school"):
                    st.markdown(f"**🎓 教育背景**：{edu.get('school', '')} | {edu.get('degree', '')} | {edu.get('major', '')} | {edu.get('graduation_time', '')}")

                # 实习经历
                internships = rp.get("internship_experience", [])
                if internships:
                    st.markdown("**💼 实习经历**")
                    for ie in internships:
                        st.markdown(f"- **{ie.get('company', '')}** | {ie.get('role', '')} | {ie.get('time', '')}")
                        if ie.get("summary"):
                            st.caption(f"  {ie['summary']}")

                # 项目经历
                projects = rp.get("projects", [])
                if projects:
                    st.markdown("**🛠 项目经历**")
                    for p in projects:
                        st.markdown(f"- **{p.get('name', '')}**（{p.get('role', '')}）")
                        if p.get("summary"):
                            st.caption(f"  {p['summary']}")

                # 技能标签
                st.markdown("**🏷 技能标签**")
                skill_sections = [
                    ("硬技能", rp.get("hard_skills", []), "chip-purple"),
                    ("AI 技能", rp.get("ai_skills", []), "chip-blue"),
                    ("产品技能", rp.get("product_skills", []), "chip-green"),
                    ("数据技能", rp.get("data_skills", []), "chip-amber"),
                ]
                cols = st.columns(4)
                for idx, (label, skills, chip_class) in enumerate(skill_sections):
                    with cols[idx]:
                        st.markdown(f"*{label}*")
                        if skills:
                            chips = "".join(f'<span class="skill-chip {chip_class}">{s}</span>' for s in skills)
                            st.markdown(chips, unsafe_allow_html=True)
                        else:
                            st.caption("—")

                # 弱项
                weaknesses = rp.get("weaknesses", [])
                if weaknesses:
                    st.markdown(f"**⚠️ 当前短板**：{'、'.join(weaknesses)}")

            with c2:
                if st.button("🔄 重新解析简历", use_container_width=True):
                    st.session_state["resume_raw_text"] = ""
                    st.session_state["resume_profile"] = None
                    st.rerun()
        else:
            # 未解析，显示输入框
            resume_text = st.text_area(
                "请粘贴你的简历文本",
                value=st.session_state["resume_raw_text"],
                height=300,
                placeholder="在此粘贴你的完整简历...",
                key="resume_input",
            )

            if st.button("🔍 解析简历", type="primary", disabled=not resume_text.strip()):
                with st.spinner("正在解析简历..."):
                    result = parse_resume(resume_text)
                if result and result.get("success"):
                    st.session_state["resume_profile"] = result["resume_profile"]
                    st.session_state["resume_raw_text"] = resume_text
                    st.rerun()
                else:
                    st.error("解析失败，请检查后端服务后重试")

    st.divider()

    # ═══════════════════════════════════════════
    # 岗位列表
    # ═══════════════════════════════════════════

    jobs = load_jobs()
    if not jobs:
        st.info("暂无数据。请在 BOSS 直聘岗位详情页点击书签栏的「一键分析」开始采集。")
        return

    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)

    if selected_category != "全部":
        jobs = [j for j in jobs if j.get("analysis", {}).get("category") == selected_category]
    if selected_city != "全部":
        jobs = [j for j in jobs if j.get("city") == selected_city]
    if selected_company != "全部":
        jobs = [j for j in jobs if j.get("company") == selected_company]

    if not jobs:
        st.info(f"没有匹配「{selected_category}」+「{selected_city}」+「{selected_company}」的岗位。")
        return

    # ── 岗位卡片 ──
    for job in jobs:
        analysis = job.get("analysis", {})
        category = analysis.get("category", "未分类")
        color = COLORS.get(category, "#6b7280")
        job_id = job.get("id", "")

        with st.container(border=True):
            detail_key = f"show_detail_{job_id}"
            if detail_key not in st.session_state:
                st.session_state[detail_key] = False

            # ── 标题行 ──
            tc0, tc1, tc2, tc3, tc4, tc5 = st.columns([0.3, 2.5, 1.2, 1.5, 1, 0.8])
            with tc0:
                arrow = "▼" if st.session_state[detail_key] else "▶"
                if st.button(arrow, key=f"toggle_{job_id}", help="展开/收起详情"):
                    st.session_state[detail_key] = not st.session_state[detail_key]
                    st.rerun()
            with tc1:
                st.markdown(f"**{job.get('jobName', '未知岗位')}**")
            with tc2:
                st.markdown(f"💰 {job.get('salary', '面议')}")
            with tc3:
                st.markdown(f"🏢 {job.get('company', '未知公司')}  |  📍 {job.get('city', '未知城市')}")
            with tc4:
                st.markdown(
                    f"<span style='background:{color};color:#fff;padding:2px 12px;border-radius:12px;font-size:13px;'>{category}</span>",
                    unsafe_allow_html=True,
                )
            with tc5:
                confirm_key = f"confirm_{job_id}"
                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False
                if not st.session_state[confirm_key]:
                    if st.button("🗑️ 删除", key=f"del_{job_id}"):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        if st.button("✅ 确认", key=f"confirm_yes_{job_id}"):
                            if delete_job(job_id):
                                st.session_state[confirm_key] = False
                                st.rerun()
                            else:
                                st.error("删除失败")
                    with bc2:
                        if st.button("❌ 取消", key=f"confirm_no_{job_id}"):
                            st.session_state[confirm_key] = False
                            st.rerun()

            # ═══════════════════════════════════════════
            # 2.0 新增：匹配度分析按钮（标题行下方）
            # ═══════════════════════════════════════════
            has_resume = st.session_state["resume_profile"] is not None
            if not has_resume:
                st.caption("💡 请先在上方「我的简历 Profile」中解析简历，然后生成匹配度分析")
            else:
                match_btn_col, _ = st.columns([1.5, 5])
                with match_btn_col:
                    if st.button(f"📊 生成匹配度分析", key=f"match_{job_id}", type="secondary"):
                        with st.spinner("正在分析匹配度..."):
                            result = match_resume_job(job_id)
                        if result and result.get("success"):
                            st.session_state["match_reports"][job_id] = result["match_report"]
                            st.rerun()
                        else:
                            st.error("匹配分析失败，请检查后端服务")

            # ── 匹配报告展示 ──
            match_report = st.session_state["match_reports"].get(job_id)
            if match_report:
                st.markdown('<hr class="divider-gradient">', unsafe_allow_html=True)
                mr = match_report
                overall = mr.get("overall_score", 0)

                # ── 总分行：环形评分 + 建议 ──
                gauge_color = (
                    "#10b981" if overall >= 80 else
                    "#6366f1" if overall >= 65 else
                    "#f59e0b" if overall >= 50 else
                    "#ef4444"
                )
                rec = mr.get("recommendation", "")
                conf = mr.get("confidence", "medium")
                conf_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(conf, "🟡")

                gm1, gm2 = st.columns([1.5, 3])
                with gm1:
                    st.markdown(f"""
                    <div style="background:linear-gradient(135deg, #1e1b4b, #312e81);border-radius:16px;padding:28px 20px;text-align:center;">
                        <div style="font-size:13px;color:#a5b4fc;margin-bottom:6px;text-transform:uppercase;letter-spacing:2px;">匹配度评分</div>
                        <div style="font-size:56px;font-weight:800;color:{gauge_color};line-height:1;">{overall}</div>
                        <div style="font-size:16px;color:#94a3b8;">/ 100</div>
                    </div>
                    """, unsafe_allow_html=True)
                with gm2:
                    st.markdown(f"""
                    <div style="background:white;border-radius:14px;padding:24px;border:1px solid #e2e8f0;height:100%;display:flex;flex-direction:column;justify-content:center;">
                        <div style="font-size:15px;color:#475569;margin-bottom:8px;">{conf_icon} 置信度：<strong>{conf}</strong></div>
                        <div style="font-size:14px;color:#1e293b;padding:10px 14px;background:#f8fafc;border-radius:8px;border-left:3px solid {gauge_color};">{rec}</div>
                    </div>
                    """, unsafe_allow_html=True)

                # ── 五维评分明细 ──
                st.markdown("")
                score_bd = mr.get("score_breakdown", {})
                dim_config = [
                    ("ai_product_ability", "🧠 AI 产品能力 (30%)"),
                    ("project_relevance", "🎯 项目相关性 (25%)"),
                    ("product_fundamentals", "📋 产品基本功 (20%)"),
                    ("data_analysis", "📊 数据分析 (15%)"),
                    ("keyword_coverage", "🔑 关键词覆盖 (10%)"),
                ]
                for dim_key, dim_label in dim_config:
                    item = score_bd.get(dim_key, {})
                    dim_score = item.get("score", 0)
                    bar_color = (
                        "#10b981" if dim_score >= 80 else
                        "#6366f1" if dim_score >= 60 else
                        "#f59e0b" if dim_score >= 40 else
                        "#ef4444"
                    )
                    st.markdown(f"""
                    <div style="margin-bottom:10px;">
                        <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                            <span style="font-size:13px;font-weight:600;color:#334155;">{dim_label}</span>
                            <span style="font-size:13px;font-weight:700;color:{bar_color};">{dim_score} 分</span>
                        </div>
                        <div style="background:#e2e8f0;border-radius:100px;height:6px;">
                            <div style="width:{dim_score}%;height:6px;border-radius:100px;background:{bar_color};transition:width 0.5s;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if item.get("evidence"):
                        ev = " · ".join(item["evidence"])
                        st.caption(f"✅ {ev}")
                    if item.get("missing"):
                        ms = " · ".join(item["missing"])
                        st.caption(f"❌ {ms}")

                # 匹配优势 / 缺失 / 风险
                if mr.get("matched_points"):
                    st.success(f"**✅ 匹配优势**：{'；'.join(mr['matched_points'])}")
                if mr.get("missing_points"):
                    st.error(f"**❌ 能力缺口**：{'；'.join(mr['missing_points'])}")
                if mr.get("risks"):
                    st.warning(f"**⚠️ 风险提示**：{'；'.join(mr['risks'])}")
                if mr.get("action_suggestions"):
                    st.info(f"**💡 行动建议**：{'；'.join(mr['action_suggestions'])}")

                # ── 关键词覆盖分析 ──
                ka = mr.get("keyword_analysis", {})
                if ka:
                    st.markdown('<hr class="divider-gradient">', unsafe_allow_html=True)
                    st.markdown("##### 🔑 关键词覆盖分析")
                    jd_kw = [k.get("keyword", "") for k in ka.get("jd_core_keywords", [])]
                    cv_kw = ka.get("resume_covered_keywords", [])
                    ms_kw = [k.get("keyword", "") for k in ka.get("missing_keywords", [])]
                    add_kw = ka.get("recommended_keywords_to_add", [])
                    no_kw = ka.get("keywords_not_to_force", [])

                    if jd_kw:
                        chips = "".join(f'<span class="skill-chip chip-slate">{k}</span>' for k in jd_kw)
                        st.markdown(f'<div style="margin:8px 0;"><span style="font-size:13px;color:#64748b;">📌 JD 核心</span> {chips}</div>', unsafe_allow_html=True)
                    if cv_kw:
                        chips = "".join(f'<span class="skill-chip chip-green">{k}</span>' for k in cv_kw)
                        st.markdown(f'<div style="margin:8px 0;"><span style="font-size:13px;color:#64748b;">✅ 已覆盖</span> {chips}</div>', unsafe_allow_html=True)
                    if ms_kw:
                        chips = "".join(f'<span class="skill-chip chip-rose">{k}</span>' for k in ms_kw)
                        st.markdown(f'<div style="margin:8px 0;"><span style="font-size:13px;color:#64748b;">❌ 缺失</span> {chips}</div>', unsafe_allow_html=True)
                    if add_kw:
                        chips = "".join(f'<span class="skill-chip chip-blue">{k}</span>' for k in add_kw)
                        st.markdown(f'<div style="margin:8px 0;"><span style="font-size:13px;color:#64748b;">📝 建议补充</span> {chips}</div>', unsafe_allow_html=True)
                    if no_kw:
                        chips = "".join(f'<span class="skill-chip chip-amber">{k}</span>' for k in no_kw)
                        st.markdown(f'<div style="margin:8px 0;"><span style="font-size:13px;color:#64748b;">🚫 不建议强行添加</span> {chips}</div>', unsafe_allow_html=True)

                # ── 操作按钮行 ──
                st.markdown('<hr class="divider-gradient">', unsafe_allow_html=True)
                st.markdown("##### ⚡ 下一步操作")
                act1, act2, act3, act4 = st.columns([1.2, 1.1, 0.6, 0.6])
                with act1:
                    if st.button(f"✏️ 简历改写建议", key=f"rewrite_{job_id}", type="primary"):
                        with st.spinner("正在生成简历改写建议..."):
                            rw_result = generate_rewrite(job_id)
                        if rw_result and rw_result.get("success"):
                            st.session_state["rewrite_reports"][job_id] = rw_result["rewrite_report"]
                            st.rerun()
                        else:
                            st.error("简历改写生成失败")

                with act2:
                    if st.button(f"💬 生成投递话术", key=f"msg_{job_id}", type="primary"):
                        with st.spinner("正在生成投递话术..."):
                            msg_result = generate_message(job_id, match_report_id=mr.get("id", ""))
                        if msg_result and msg_result.get("success"):
                            st.session_state["messages"][job_id] = msg_result["messages"]
                            st.rerun()
                        else:
                            st.error("话术生成失败")

                match_id = mr.get("id", "")
                with act3:
                    if st.button("👍", key=f"fb_good_{match_id}", help="匹配报告有用"):
                        if submit_feedback("match_report", match_id, "useful"):
                            st.toast("👍 反馈已记录，谢谢！")
                with act4:
                    if st.button("👎", key=f"fb_bad_{match_id}", help="匹配报告不准确"):
                        if submit_feedback("match_report", match_id, "not_accurate"):
                            st.toast("反馈已记录，我们会持续改进！")

                # 展示简历改写结果
                rw_report = st.session_state["rewrite_reports"].get(job_id)
                if rw_report:
                    st.markdown('<hr class="divider-gradient">', unsafe_allow_html=True)
                    st.subheader("✏️ 简历改写建议")
                    st.caption(f"改写策略：{rw_report.get('rewrite_strategy', '')}")

                    bullets = rw_report.get("optimized_bullets", [])
                    if bullets:
                        st.markdown("**推荐 Bullet Points（可直接复制到简历）**")
                        for b in bullets:
                            st.code(b, language=None)

                    kw = rw_report.get("keywords_to_include", [])
                    if kw:
                        st.markdown(f"**建议突出关键词**：{'、'.join(kw)}")

                    metrics = rw_report.get("metrics_to_collect", [])
                    if metrics:
                        st.markdown(f"**可补充的量化指标**：{'；'.join(metrics)}")

                    warnings = rw_report.get("warnings", [])
                    if warnings:
                        for w in warnings:
                            st.warning(w)

                    # 反馈
                    fb_rw_col1, fb_rw_col2 = st.columns([0.5, 0.5])
                    with fb_rw_col1:
                        if st.button("👍 有用", key=f"fb_rw_good_{job_id}"):
                            if submit_feedback("resume_rewrite", job_id, "useful"):
                                st.toast("反馈已记录")
                    with fb_rw_col2:
                        if st.button("👎 不准确", key=f"fb_rw_bad_{job_id}"):
                            if submit_feedback("resume_rewrite", job_id, "not_accurate"):
                                st.toast("反馈已记录")

                # 展示投递话术
                msg_data = st.session_state["messages"].get(job_id)
                if msg_data:
                    st.markdown('<hr class="divider-gradient">', unsafe_allow_html=True)
                    st.subheader("💬 投递话术")

                    boss_msg = msg_data.get("boss_zhipin_opening", "")
                    if boss_msg:
                        st.markdown("**Boss 直聘开场白**")
                        st.text_area("（可复制）", boss_msg, height=120, key=f"boss_{job_id}")

                    email_msg = msg_data.get("email_body", "")
                    if email_msg:
                        st.markdown("**邮件正文**")
                        st.text_area("（可复制）", email_msg, height=200, key=f"email_{job_id}")

                    ref_msg = msg_data.get("referral_message", "")
                    if ref_msg:
                        st.markdown("**内推私信**")
                        st.text_area("（可复制）", ref_msg, height=120, key=f"ref_{job_id}")

                    # 反馈
                    fb_msg_col1, fb_msg_col2 = st.columns([0.5, 0.5])
                    with fb_msg_col1:
                        if st.button("👍 有用", key=f"fb_msg_good_{job_id}"):
                            if submit_feedback("application_message", job_id, "useful"):
                                st.toast("反馈已记录")
                    with fb_msg_col2:
                        if st.button("👎 不准确", key=f"fb_msg_bad_{job_id}"):
                            if submit_feedback("application_message", job_id, "not_accurate"):
                                st.toast("反馈已记录")

            # ── 岗位详情展开 ──
            if st.session_state[detail_key]:
                st.divider()

                jd_text = job.get("raw_jd", "")
                html_parts = []
                for line in jd_text.split("\n"):
                    line_s = line.strip()
                    if not line_s:
                        html_parts.append('<div style="height:8px"></div>')
                        continue
                    if any(line_s.startswith(kw) for kw in
                           ["职位描述", "岗位职责", "工作职责", "职责描述",
                            "职位要求", "任职要求", "任职资格", "岗位要求",
                            "团队介绍", "部门介绍", "公司介绍"]):
                        html_parts.append(
                            f'<div style="color:#2563eb;font-weight:700;'
                            f'font-size:15px;margin-top:12px;margin-bottom:4px;'
                            f'padding-bottom:4px;border-bottom:1px solid #dbeafe;">'
                            f'{line_s}</div>'
                        )
                    else:
                        html_parts.append(
                            f'<div style="color:#222;font-size:14px;'
                            f'line-height:1.8;margin:2px 0;">{line_s}</div>'
                        )
                st.markdown(
                    f"<div style='background:#fafbfc;padding:16px 20px;"
                    f"border-radius:8px;border:1px solid #e5e7eb;'>"
                    f"{''.join(html_parts)}</div>",
                    unsafe_allow_html=True,
                )

                st.divider()
                st.markdown(f"**📝 分类依据**：{analysis.get('reason', '无')}")

                skills = analysis.get("hard_skills", [])
                if skills:
                    st.markdown("**🛠 核心硬技能**")
                    chips = "".join(f'<span class="skill-chip chip-blue">{s}</span>' for s in skills)
                    st.markdown(chips, unsafe_allow_html=True)

                hidden = analysis.get("hidden_requirements", "")
                if hidden:
                    st.warning(f"**⚠️ 隐藏卡点**：{hidden}")

                questions = analysis.get("interview_questions", [])
                if questions:
                    st.markdown("**🎯 定制化面试三问**")
                    for i, q in enumerate(questions, 1):
                        st.markdown(f"{i}. {q}")

                st.caption(f"📅 {job.get('created_at', '')}  |  ID: {job_id}")


if __name__ == "__main__":
    main()
