def load_prompt(name: str, default: str) -> str:
    from pathlib import Path

    path = Path(__file__).resolve().parents[3] / "prompts" / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return default
