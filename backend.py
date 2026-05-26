import json
import os
import time
import threading
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from anthropic import Anthropic

from prompts import (
    SYSTEM_PROMPT,
    COMPARE_PROMPT,
    PARSE_RESUME_PROMPT,
    MATCH_RESUME_JOB_PROMPT,
    RESUME_REWRITE_PROMPT,
    APPLICATION_MESSAGE_PROMPT,
)

load_dotenv()

app = FastAPI(title="JD Analysis API 2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 数据文件路径 ──
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
JOBS_FILE = os.path.join(DATA_DIR, "jobs.json")
RESUME_FILE = os.path.join(DATA_DIR, "resume_profile.json")
MATCH_REPORTS_FILE = os.path.join(DATA_DIR, "match_reports.json")
FEEDBACK_FILE = os.path.join(DATA_DIR, "feedback_logs.json")

# 兼容旧版：迁移根目录 jobs.json 到 data/
_old_jobs = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs.json")
if os.path.exists(_old_jobs) and not os.path.exists(JOBS_FILE):
    import shutil
    shutil.copy2(_old_jobs, JOBS_FILE)

file_lock = threading.Lock()

llm_client = Anthropic(
    api_key=os.getenv("LLM_API_KEY", "sk-xxx"),
    base_url=os.getenv("LLM_BASE_URL", "https://api.anthropic.com"),
)
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

# ═══════════════════════════════════════════
# 通用工具函数
# ═══════════════════════════════════════════

def safe_parse_json(text: str) -> dict:
    """安全解析 LLM 返回的 JSON，支持 Markdown 代码块包裹"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:]) if len(lines) > 1 else text
    if text.endswith("```"):
        text = text[: text.rfind("```")].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start:end + 1])
    raise ValueError(f"无法解析 LLM 输出为 JSON: {text[:300]}")


def load_json_file(filepath: str) -> list:
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_json_file(filepath: str, data: list) -> None:
    with file_lock:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def append_json_file(filepath: str, record: dict) -> None:
    data = load_json_file(filepath)
    data.append(record)
    save_json_file(filepath, data)


# ═══════════════════════════════════════════
# 评分函数
# ═══════════════════════════════════════════

DEFAULT_AI_PM_WEIGHTS = {
    "ai_product_ability": 0.30,
    "project_relevance": 0.25,
    "product_fundamentals": 0.20,
    "data_analysis": 0.15,
    "keyword_coverage": 0.10,
}


def calculate_overall_score(score_breakdown: dict, weight_config: dict = None) -> int:
    if weight_config is None:
        weight_config = DEFAULT_AI_PM_WEIGHTS
    total = 0.0
    for dim, weight in weight_config.items():
        dim_score = score_breakdown.get(dim, {}).get("score", 0)
        total += dim_score * weight
    return round(total)


def get_recommendation(score: int) -> str:
    if score >= 80:
        return "高度匹配，建议优先投递"
    elif score >= 65:
        return "基本匹配，建议投递，但需要优化简历表达"
    elif score >= 50:
        return "谨慎投递，建议先补关键能力或调整简历"
    else:
        return "暂不建议投递，当前缺口较大"


# ═══════════════════════════════════════════
# LLM 调用
# ═══════════════════════════════════════════

def call_llm_raw(system_prompt: str, user_content: str, max_tokens: int = 4096) -> str:
    response = llm_client.messages.create(
        model=LLM_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
        temperature=0.3,
        thinking={"type": "disabled"},
    )
    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text
    return text


def call_llm_and_parse(system_prompt: str, user_content: str, max_tokens: int = 4096) -> dict:
    text = call_llm_raw(system_prompt, user_content, max_tokens)
    return safe_parse_json(text)


# ═══════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════

class JobInput(BaseModel):
    jobName: str
    salary: str = ""
    company: str = ""
    city: str = ""
    raw_jd: str


class AnalyzeRequest(BaseModel):
    job_ids: list[str]


class ParseResumeRequest(BaseModel):
    resume_text: str


class MatchResumeJobRequest(BaseModel):
    job_id: str
    resume_id: str = ""


class GenerateResumeRewriteRequest(BaseModel):
    job_id: str
    resume_id: str = ""
    project_name: str = "JD智能分析与简历匹配系统"


class GenerateApplicationMessageRequest(BaseModel):
    job_id: str
    resume_id: str = ""
    match_report_id: str = ""


class SubmitFeedbackRequest(BaseModel):
    target_type: str
    target_id: str
    feedback_type: str
    comment: str = ""


# ═══════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════

def _jd_fingerprint(raw_jd: str) -> str:
    return "".join(raw_jd.split())[:200]


def _get_resume_profile() -> dict | None:
    data = load_json_file(RESUME_FILE)
    return data[-1] if data else None


def _get_latest_resume_id() -> str:
    data = load_json_file(RESUME_FILE)
    return data[-1]["id"] if data else ""


def _get_match_report(match_id: str) -> dict | None:
    data = load_json_file(MATCH_REPORTS_FILE)
    for r in data:
        if r.get("id") == match_id:
            return r
    return None


# ═══════════════════════════════════════════
# v1 端点
# ═══════════════════════════════════════════

@app.post("/add_job")
async def add_job(job: JobInput):
    if not job.raw_jd.strip() or not job.jobName.strip():
        raise HTTPException(status_code=400, detail="jobName 和 raw_jd 为必填字段")

    jobs = load_json_file(JOBS_FILE)
    fp = _jd_fingerprint(job.raw_jd)

    for existing in jobs:
        if _jd_fingerprint(existing.get("raw_jd", "")) == fp:
            return {
                "status": "ok",
                "id": existing["id"],
                "analysis": existing["analysis"],
                "duplicate": True,
            }

    try:
        analysis = call_llm_and_parse(SYSTEM_PROMPT, job.raw_jd)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 分析失败: {e}")

    job_id = f"job_{int(time.time() * 1000)}"
    record = {
        "id": job_id,
        "jobName": job.jobName,
        "salary": job.salary,
        "company": job.company,
        "city": job.city,
        "raw_jd": job.raw_jd,
        "analysis": analysis,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    jobs.append(record)
    save_json_file(JOBS_FILE, jobs)

    return {"status": "ok", "id": job_id, "analysis": analysis, "duplicate": False}


@app.get("/jobs")
async def get_jobs():
    return load_json_file(JOBS_FILE)


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    jobs = load_json_file(JOBS_FILE)
    new_jobs = [j for j in jobs if j.get("id") != job_id]
    if len(new_jobs) == len(jobs):
        raise HTTPException(status_code=404, detail="岗位不存在")
    save_json_file(JOBS_FILE, new_jobs)
    return {"status": "ok", "deleted": job_id}


@app.post("/analyze_jobs")
async def analyze_jobs(req: AnalyzeRequest):
    if not req.job_ids:
        raise HTTPException(status_code=400, detail="请至少选择一个岗位")

    all_jobs = load_json_file(JOBS_FILE)
    selected = [j for j in all_jobs if j.get("id") in req.job_ids]
    if not selected:
        raise HTTPException(status_code=404, detail="未找到匹配的岗位")

    parts = []
    for i, job in enumerate(selected, 1):
        analysis = job.get("analysis", {})
        parts.append(
            f"【岗位 {i}】公司：{job.get('company', '未知')} | "
            f"岗位名：{job.get('jobName', '未知')} | "
            f"分类：{analysis.get('category', '未分类')}\n"
            f"JD 内容：{job.get('raw_jd', '')[:3000]}"
        )
    user_content = "\n\n".join(parts)

    try:
        result = call_llm_and_parse(COMPARE_PROMPT, user_content, max_tokens=8192)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="LLM 返回格式异常")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 分析失败: {e}")

    return {
        "status": "ok",
        "analyzed_jobs": [
            {"id": j["id"], "jobName": j["jobName"], "company": j["company"]}
            for j in selected
        ],
        "analysis": result,
    }


# ═══════════════════════════════════════════
# v2 端点
# ═══════════════════════════════════════════

@app.post("/parse_resume")
async def parse_resume(req: ParseResumeRequest):
    if not req.resume_text.strip():
        raise HTTPException(status_code=400, detail="简历文本不能为空")

    user_content = PARSE_RESUME_PROMPT.replace("{{resume_text}}", req.resume_text)
    try:
        profile = call_llm_and_parse(PARSE_RESUME_PROMPT, user_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"简历解析失败: {e}")

    resume_id = f"resume_{int(time.time() * 1000)}"
    record = {
        "id": resume_id,
        "raw_text": req.resume_text,
        **profile,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    append_json_file(RESUME_FILE, record)

    return {"success": True, "resume_profile": record}


@app.post("/match_resume_job")
async def match_resume_job(req: MatchResumeJobRequest):
    jobs = load_json_file(JOBS_FILE)
    job = next((j for j in jobs if j.get("id") == req.job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="岗位不存在")

    if req.resume_id:
        resumes = load_json_file(RESUME_FILE)
        resume = next((r for r in resumes if r.get("id") == req.resume_id), None)
    else:
        resume = _get_resume_profile()
    if not resume:
        raise HTTPException(status_code=400, detail="请先解析简历")

    job_analysis = job.get("analysis", {})
    user_content = (
        MATCH_RESUME_JOB_PROMPT
        .replace("{{job_analysis}}", json.dumps(job_analysis, ensure_ascii=False))
        .replace("{{resume_profile}}", json.dumps(resume, ensure_ascii=False))
    )
    try:
        match_data = call_llm_and_parse(MATCH_RESUME_JOB_PROMPT, user_content, max_tokens=8192)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匹配分析失败: {e}")

    overall_score = calculate_overall_score(match_data.get("score_breakdown", {}))
    recommendation = match_data.get("recommendation") or get_recommendation(overall_score)

    match_id = f"match_{int(time.time() * 1000)}"
    match_report = {
        "id": match_id,
        "job_id": req.job_id,
        "resume_id": resume["id"],
        "job_category": match_data.get("job_category", ""),
        "weight_config": DEFAULT_AI_PM_WEIGHTS,
        "score_breakdown": match_data.get("score_breakdown", {}),
        "overall_score": overall_score,
        "recommendation": recommendation,
        "confidence": match_data.get("confidence", "medium"),
        "matched_points": match_data.get("matched_points", []),
        "missing_points": match_data.get("missing_points", []),
        "risks": match_data.get("risks", []),
        "action_suggestions": match_data.get("action_suggestions", []),
        "keyword_analysis": match_data.get("keyword_analysis", {}),
        "score_explanation": match_data.get(
            "score_explanation",
            "该分数基于 JD 显性要求、简历内容和 AI 产品经理岗位能力模型综合计算，仅用于辅助判断岗位适配度，不代表招聘方真实筛选结果。",
        ),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    append_json_file(MATCH_REPORTS_FILE, match_report)

    return {"success": True, "match_report": match_report}


@app.post("/generate_resume_rewrite")
async def generate_resume_rewrite(req: GenerateResumeRewriteRequest):
    jobs = load_json_file(JOBS_FILE)
    job = next((j for j in jobs if j.get("id") == req.job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="岗位不存在")

    if req.resume_id:
        resumes = load_json_file(RESUME_FILE)
        resume = next((r for r in resumes if r.get("id") == req.resume_id), None)
    else:
        resume = _get_resume_profile()
    if not resume:
        raise HTTPException(status_code=400, detail="请先解析简历")

    user_content = (
        RESUME_REWRITE_PROMPT
        .replace("{{job_analysis}}", json.dumps(job.get("analysis", {}), ensure_ascii=False))
        .replace("{{resume_profile}}", json.dumps(resume, ensure_ascii=False))
        .replace("{{project_name}}", req.project_name)
    )
    try:
        rewrite = call_llm_and_parse(RESUME_REWRITE_PROMPT, user_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"简历改写失败: {e}")

    return {"success": True, "rewrite_report": rewrite}


@app.post("/generate_application_message")
async def generate_application_message(req: GenerateApplicationMessageRequest):
    jobs = load_json_file(JOBS_FILE)
    job = next((j for j in jobs if j.get("id") == req.job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="岗位不存在")

    if req.resume_id:
        resumes = load_json_file(RESUME_FILE)
        resume = next((r for r in resumes if r.get("id") == req.resume_id), None)
    else:
        resume = _get_resume_profile()
    if not resume:
        raise HTTPException(status_code=400, detail="请先解析简历")

    match_report = {}
    if req.match_report_id:
        match_report = _get_match_report(req.match_report_id) or {}
    else:
        reports = load_json_file(MATCH_REPORTS_FILE)
        if reports:
            match_report = reports[-1]

    user_content = (
        APPLICATION_MESSAGE_PROMPT
        .replace("{{job_analysis}}", json.dumps(job.get("analysis", {}), ensure_ascii=False))
        .replace("{{resume_profile}}", json.dumps(resume, ensure_ascii=False))
        .replace("{{match_report}}", json.dumps(match_report, ensure_ascii=False))
    )
    try:
        messages = call_llm_and_parse(APPLICATION_MESSAGE_PROMPT, user_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"话术生成失败: {e}")

    return {"success": True, "messages": messages}


@app.post("/submit_feedback")
async def submit_feedback(req: SubmitFeedbackRequest):
    record = {
        "id": f"feedback_{int(time.time() * 1000)}",
        "target_type": req.target_type,
        "target_id": req.target_id,
        "feedback_type": req.feedback_type,
        "comment": req.comment,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    append_json_file(FEEDBACK_FILE, record)
    return {"success": True, "message": "反馈已记录"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
