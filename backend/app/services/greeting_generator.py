from .llm import LLMError, complete_text
from .prompts import load_prompt


DEFAULT_TEMPLATE = """您好，我对贵司的 {title} 岗位很感兴趣。我的背景与岗位要求较匹配，简历已附上，期待进一步沟通。"""


def generate_greeting(company: str, title: str, resume_text: str, jd_text: str) -> str:
    prompt_template = load_prompt(
        "greeting_boss.md",
        "根据岗位 JD 和简历亮点，生成一条不超过100字的中文打招呼语。\n公司：{company}\n岗位：{title}\nJD：{jd}\n简历：{resume}",
    )
    return complete_text(
        prompt_template.format(company=company, title=title, jd=jd_text[:4000], resume=resume_text[:4000])
    ).strip()
