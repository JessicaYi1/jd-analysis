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

load_dotenv()

app = FastAPI(title="JD Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs.json")
file_lock = threading.Lock()

llm_client = Anthropic(
    api_key=os.getenv("LLM_API_KEY", "sk-xxx"),
    base_url=os.getenv("LLM_BASE_URL", "https://api.anthropic.com"),
)
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

SYSTEM_PROMPT = """# 角色
你是一个精通互联网产品经理招聘的资深技术专家与猎头顾问。

# 任务
阅读用户提供的原始【职位描述（JD）】，从下述【标准分类池】中选择一个最精准的标签归类。必须严格返回 JSON，不得返回任何 Markdown 标记或解释性文字。

# 标准分类池（必须严格从以下 4 个中选择，禁止自行创造）
- AI产品经理 (核心关键词：大模型、LLM、Agent、Prompt、NLP/语音/图像算法、数据标注、模型评测等)
- 策略产品经理 (核心关键词：推荐算法、搜索、风控、动态定价、AB测试、特征工程、策略分流等)
- 中后台产品经理 (核心关键词：ERP、CRM、WMS、供应链、财务系统、权限管理、低代码平台、清结算等)
- 通用PM/前台产品经理 (核心关键词：电商C端、社交、内容社区、增长、短视频、APP核心链路、用户体验等)

# 预期输出 JSON 格式
{
  "category": "分类池中的一个",
  "reason": "归类原因（30字以内）",
  "hard_skills": ["提取 3 个核心硬技能标签"],
  "hidden_requirements": "分析出 JD 字面背后没有直接写明的隐藏硬性要求或卡点",
  "interview_questions": ["针对该细分方向和公司业务，定制 3 个最可能被问到的硬核面试问题"]
}"""


class JobInput(BaseModel):
    jobName: str
    salary: str = ""
    company: str = ""
    city: str = ""
    raw_jd: str


def load_jobs() -> list[dict]:
    if not os.path.exists(JOBS_FILE):
        return []
    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_jobs(jobs: list[dict]) -> None:
    with file_lock:
        with open(JOBS_FILE, "w", encoding="utf-8") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)


def call_llm(raw_jd: str) -> dict:
    response = llm_client.messages.create(
        model=LLM_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": raw_jd}],
        temperature=0.3,
        thinking={"type": "disabled"},
    )
    # 提取所有 TextBlock 的文本内容（跳过 ThinkingBlock）
    text = ""
    for block in response.content:
        if block.type == "text":
            text += block.text
    # 清理可能的 markdown 代码块标记
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:]) if len(lines) > 1 else text
    if text.endswith("```"):
        text = text[: text.rfind("```")].strip()
    return json.loads(text)


def _jd_fingerprint(raw_jd: str) -> str:
    """取 JD 前 200 个非空白字符作为轻量指纹"""
    return "".join(raw_jd.split())[:200]


@app.post("/add_job")
async def add_job(job: JobInput):
    if not job.raw_jd.strip() or not job.jobName.strip():
        raise HTTPException(status_code=400, detail="jobName 和 raw_jd 为必填字段")

    jobs = load_jobs()
    fp = _jd_fingerprint(job.raw_jd)

    # 去重检测
    for existing in jobs:
        if _jd_fingerprint(existing.get("raw_jd", "")) == fp:
            return {
                "status": "ok",
                "id": existing["id"],
                "analysis": existing["analysis"],
                "duplicate": True,
            }

    try:
        analysis = call_llm(job.raw_jd)
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
    save_jobs(jobs)

    return {"status": "ok", "id": job_id, "analysis": analysis, "duplicate": False}


@app.get("/jobs")
async def get_jobs():
    return load_jobs()


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    jobs = load_jobs()
    new_jobs = [j for j in jobs if j.get("id") != job_id]
    if len(new_jobs) == len(jobs):
        raise HTTPException(status_code=404, detail="岗位不存在")
    save_jobs(new_jobs)
    return {"status": "ok", "deleted": job_id}


COMPARE_PROMPT = """# 角色
你是一个专精互联网产品经理（尤其是 AI 产品经理）求职辅导的资深职业规划师。
你的用户画像：零基础或跨行业、想要转行产品经理的小白，没有技术背景，不了解岗位术语。

# 任务
阅读下方用户提供的【多个目标岗位的 JD 合集】，站在「零基础转行入门 → 达到这些岗位的门槛要求」的角度，输出一份全面的差距分析与提升方案。

# 硬性约束
- 必须严格返回 JSON，不得返回任何 Markdown 标记或解释性文字
- 综合分析所有岗位，找出共性要求和高频关键词，**禁止**逐条单独罗列
- 每条建议都要具体可执行，**禁止**出现"多学习、多实践、多看文章"等空话
- 提到任何专业术语时，必须在上下文中用括号给出 1 句话大白话解释
- 技能分析必须标注在所有岗位中出现的频次比例，作为优先级判断依据
- 学习路径必须有明确的阶段顺序，后一阶段依赖前一阶段的能力

# 分析维度与质量标准

## summary（必须）
2-3 句话画出这批岗位的人才画像：招什么人、看重什么、门槛在哪。
好的示例："这 5 个岗位集中招 AI 方向产品实习生，核心要求是 LLM 基础认知 + 动手评测能力 + 数据分析基础，学历卡本科但专业偏好计算机/工程类。对实际 AI 项目落地经验的重视程度超过传统产品 sense。"

## must_have_skills（必须，3-5 个）
缺了直接过不了简历关的硬技能。每条必须给出：
- frequency: 精确统计岗位占比，如"5 个岗位中 4 个明确要求"
- why: 一句话说明为什么这是硬门槛（不是 JD 写了什么，而是背后的筛选逻辑）
- how_to_learn: 给具体资源名称和学习范围，如"看吴恩达《AI for Everyone》前 3 周 + 用 Coze 搭 1 个 Agent 实操"，**禁止**只说"网上找课程"

## bonus_skills（必须，2-4 个）
掌握后显著提升简历通过率的差异化技能。质量要求同 must_have_skills。

## industry_knowledge（必须，2-3 个）
小白需要提前补的业务认知。每条必须给出具体的调研方法，如"拆解 3 款竞品的功能矩阵并写分析文档"。

## project_experience（必须，2-4 个）
从小白能力出发、从易到难排列的实战项目。每个项目必须包含：
- 输出什么可展示的成果（GitHub 仓库、分析报告、原型链接）
- 具体工具链（如：用 Cursor 写前端 + 用 Coze 搭后端 Agent）
- difficulty 分为「零基础可做」/「需先完成前面项目」
- skill_mapping 必须引用前文 must_have_skills 或 bonus_skills 中的技能名

## hard_thresholds（必须）
诚实地分析硬性门槛。severity 分三档：
- 「硬性卡死」：不满足直接被系统/HR 筛掉
- 「优先筛选」：满足者优先但非绝对
- 「软性偏好」：JD 没写但面试官会偏好
每条 workaround 必须是可操作的绕行策略，**禁止**只说"没办法"。

## interview_prep（必须，3-5 个）
基于 JD 真实高频话题。sample_question 要是真实面试中会问的原题，how_to_answer 给出 3 个要点的框架。

## learning_path（必须，3-4 阶段）
按时间线的学习路线图：
- phase 1: 2-4 周，建立基础认知（不需要写代码）
- phase 2: 4-8 周，动手项目积累
- phase 3: 2-4 周，面试备战
- 每个 actions 条目格式：「做什么」+「用什么工具/资源」+「产出什么」

# 预期输出 JSON 格式
{
  "summary": "2-3 句话画出人才画像",
  "must_have_skills": [
    {
      "skill": "技能名称",
      "frequency": "5 个岗位中 4 个明确要求",
      "why": "为什么这是硬门槛（背后的筛选逻辑）",
      "how_to_learn": "具体资源名称 + 学习范围 + 实操方式"
    }
  ],
  "bonus_skills": [
    {
      "skill": "技能名称",
      "frequency": "5 个岗位中 2 个提及",
      "why": "为什么能拉开差距",
      "how_to_learn": "具体资源名称 + 学习范围 + 实操方式"
    }
  ],
  "industry_knowledge": [
    {
      "domain": "业务领域",
      "why": "为什么需要了解",
      "how_to_build": "具体调研方法（含工具/平台/产出物）"
    }
  ],
  "project_experience": [
    {
      "project": "项目名称",
      "skill_mapping": "覆盖了 must_have_skills/bonus_skills 中的 X、Y、Z",
      "difficulty": "零基础可做 / 需先完成前面项目",
      "concrete_steps": "分步骤说明 + 工具链 + 产出物"
    }
  ],
  "hard_thresholds": [
    {
      "requirement": "硬性门槛",
      "severity": "硬性卡死 / 优先筛选 / 软性偏好",
      "workaround": "可操作的绕行策略"
    }
  ],
  "interview_prep": [
    {
      "direction": "高频面试方向",
      "sample_question": "真实面试原题",
      "how_to_answer": "3 个要点的回答框架"
    }
  ],
  "learning_path": [
    {
      "phase": 1,
      "duration": "2-4 周",
      "focus": "阶段目标",
      "actions": ["做什么 + 用什么工具/资源 + 产出什么"]
    }
  ]
}"""


class AnalyzeRequest(BaseModel):
    job_ids: list[str]


@app.post("/analyze_jobs")
async def analyze_jobs(req: AnalyzeRequest):
    if not req.job_ids:
        raise HTTPException(status_code=400, detail="请至少选择一个岗位")

    all_jobs = load_jobs()
    selected = [j for j in all_jobs if j.get("id") in req.job_ids]
    if not selected:
        raise HTTPException(status_code=404, detail="未找到匹配的岗位")

    # 拼接岗位信息
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
        response = llm_client.messages.create(
            model=LLM_MODEL,
            max_tokens=8192,
            system=COMPARE_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            temperature=0.3,
            thinking={"type": "disabled"},
        )
        text = ""
        for block in response.content:
            if block.type == "text":
                text += block.text
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]) if len(lines) > 1 else text
        if text.endswith("```"):
            text = text[: text.rfind("```")].strip()
        result = json.loads(text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"LLM 返回格式异常: {text[:500]}")
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
