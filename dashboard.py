import json
import os

import requests
import streamlit as st

JOBS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs.json")

st.set_page_config(page_title="岗位智能分析看板", page_icon="📊", layout="wide")

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


def load_jobs() -> list[dict]:
    if not os.path.exists(JOBS_FILE):
        return []
    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    st.title("📊 岗位智能分析看板")
    st.caption("数据来源：BOSS 直聘 → 浏览器书签采集 → LLM 自动分类")

    # ── 侧边栏 ──
    with st.sidebar:
        st.header("🔍 筛选条件")
        selected_category = st.selectbox("细分方向", CATEGORIES, index=0)

        st.divider()
        st.caption("📌 使用方法")
        st.caption("1. 在 BOSS 直聘岗位详情页点击书签")
        st.caption("2. 数据自动发送至后端分析")
        st.caption("3. 刷新本页面查看结果")

        if st.button("🔄 手动刷新", use_container_width=True):
            st.rerun()

        job_count = len(load_jobs())
        st.metric("已收录岗位", job_count)

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

    # ── 主区域 ──
    jobs = load_jobs()

    # ── 分析结果展示 ──
    if "compare_result" in st.session_state and st.session_state["compare_result"]:
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
                    del st.session_state["compare_result"]
                    st.rerun()
            st.divider()

            # Summary
            if analysis.get("summary"):
                st.info(analysis["summary"])

            # Must-have skills
            must_have = analysis.get("must_have_skills", [])
            if must_have:
                st.markdown("### 🔴 必须技能")
                for s in must_have:
                    with st.expander(f"{s.get('skill', '')} （{s.get('frequency', '')}）", expanded=False):
                        st.markdown(f"**为什么必须**：{s.get('why', '')}")
                        st.markdown(f"**怎么学**：{s.get('how_to_learn', '')}")

            # Bonus skills
            bonus = analysis.get("bonus_skills", [])
            if bonus:
                st.markdown("### 🟡 加分技能")
                for s in bonus:
                    with st.expander(f"{s.get('skill', '')} （{s.get('frequency', '')}）", expanded=False):
                        st.markdown(f"**为什么加分**：{s.get('why', '')}")
                        st.markdown(f"**怎么学**：{s.get('how_to_learn', '')}")

            # Industry knowledge
            ind = analysis.get("industry_knowledge", [])
            if ind:
                st.markdown("### 🏭 行业认知")
                for item in ind:
                    with st.expander(item.get("domain", ""), expanded=False):
                        st.markdown(f"**为什么需要**：{item.get('why', '')}")
                        st.markdown(f"**如何建立**：{item.get('how_to_build', '')}")

            # Project experience
            proj = analysis.get("project_experience", [])
            if proj:
                st.markdown("### 🛠 项目实战建议")
                for p in proj:
                    diff = p.get("difficulty", "")
                    label = f"{'🔵' if diff == '入门' else '🟣'} {p.get('project', '')}（{diff}）"
                    with st.expander(label, expanded=False):
                        st.markdown(f"**覆盖能力**：{p.get('skill_mapping', '')}")
                        st.markdown(f"**具体步骤**：{p.get('concrete_steps', '')}")

            # Hard thresholds
            thresholds = analysis.get("hard_thresholds", [])
            if thresholds:
                st.markdown("### ⚠️ 硬性门槛")
                for t in thresholds:
                    sev = t.get("severity", "")
                    icon = "🔴" if "卡死" in sev else ("🟡" if "筛选" in sev else "🟢")
                    with st.expander(f"{icon} {t.get('requirement', '')} — {sev}", expanded=False):
                        st.markdown(f"**破局方法**：{t.get('workaround', '')}")

            # Interview prep
            iv = analysis.get("interview_prep", [])
            if iv:
                st.markdown("### 🎯 面试准备")
                for item in iv:
                    with st.expander(item.get("direction", ""), expanded=False):
                        st.markdown(f"**典型问题**：{item.get('sample_question', '')}")
                        st.markdown(f"**答题思路**：{item.get('how_to_answer', '')}")

            # Learning path
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

    if not jobs:
        st.info("暂无数据。请在 BOSS 直聘岗位详情页点击书签栏的「一键分析」开始采集。")
        return

    # 按时间倒序
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)

    # 过滤
    if selected_category != "全部":
        jobs = [j for j in jobs if j.get("analysis", {}).get("category") == selected_category]

    if not jobs:
        st.info(f"没有匹配「{selected_category}」标签的岗位。")
        return

    # ── 岗位卡片 ──
    for job in jobs:
        analysis = job.get("analysis", {})
        category = analysis.get("category", "未分类")
        color = COLORS.get(category, "#6b7280")
        job_id = job.get("id", "")

        with st.container(border=True):
            # ── 展开状态初始化 ──
            detail_key = f"show_detail_{job_id}"
            if detail_key not in st.session_state:
                st.session_state[detail_key] = False

            # ── 标题行：▶/▼ + 岗位名 + 薪资 + 公司城市 + 标签 + 删除按钮 ──
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
                # 二次确认逻辑
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
                                st.success("已删除")
                                st.rerun()
                            else:
                                st.error("删除失败")
                    with bc2:
                        if st.button("❌ 取消", key=f"confirm_no_{job_id}"):
                            st.session_state[confirm_key] = False
                            st.rerun()

            if st.session_state[detail_key]:
                st.divider()

                # 完整职位描述
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
                    cols = st.columns(len(skills))
                    for i, skill in enumerate(skills):
                        with cols[i]:
                            st.info(skill)

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
