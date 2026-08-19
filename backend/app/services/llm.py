import json
import re

from openai import OpenAI

from ..config import settings


class LLMError(RuntimeError):
    pass


def _is_local():
    return "localhost" in settings.llm_base_url or "127.0.0.1" in settings.llm_base_url


def _client() -> OpenAI:
    if not settings.llm_api_key and not _is_local():
        raise LLMError(
            "未配置 LLM：请在 backend/.env 设置 LLM_API_KEY，"
            "或设置本地 Ollama 的 LLM_BASE_URL。"
        )
    return OpenAI(
        api_key=settings.llm_api_key or "local",
        base_url=settings.llm_base_url or None,
    )


def complete_text(prompt: str, system: str | None = None) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = _client().chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=0.2,
    )
    return resp.choices[0].message.content or ""


def complete_json(prompt: str, system: str | None = None) -> dict:
    text = complete_text(prompt, system)
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise LLMError("LLM 返回内容不是 JSON。")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise LLMError(f"LLM JSON 解析失败: {exc}") from exc

