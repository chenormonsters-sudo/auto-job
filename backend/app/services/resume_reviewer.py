from ..config import settings
from .llm import complete_text
from .prompts import load_prompt


DEFAULT_PROMPT = """你是资深 HR 和简历优化专家。请审查以下简历，输出：
1. 总体评价
2. 逐段问题
3. 可执行修改建议
4. 如果提供 JD，给出岗位匹配度和针对性建议

简历：
{resume}

JD：
{job}
"""


def review_resume(resume_text: str, job_text: str | None = None) -> str:
    prompt_template = load_prompt("resume_review.md", DEFAULT_PROMPT)
    prompt = prompt_template.format(resume=resume_text[:12000], job=job_text or "（未提供）")
    return complete_text(prompt)

