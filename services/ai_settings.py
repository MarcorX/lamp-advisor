"""
AI provider settings — loaded from settings.json (overrides .env).
Supports: anthropic, openai, local (any OpenAI-compatible server).
"""
import json
import os
from pathlib import Path

SETTINGS_FILE = Path("./settings.json")

PROVIDER_DEFAULTS = {
    "anthropic": {
        "model": "claude-sonnet-4-6",
        "base_url": "",
    },
    "openai": {
        "model": "gpt-4o",
        "base_url": "",
    },
    "local": {
        "model": "llama3",
        "base_url": "http://localhost:11434/v1",
    },
}

DEFAULTS = {
    "provider": "anthropic",
    "model":    "claude-sonnet-4-6",
    "api_key":  "",
    "base_url": "",
}


def load() -> dict:
    s = dict(DEFAULTS)

    # 1. Environment variables as initial defaults
    if os.getenv("AI_PROVIDER"):  s["provider"] = os.getenv("AI_PROVIDER")
    if os.getenv("AI_MODEL"):     s["model"]    = os.getenv("AI_MODEL")
    if os.getenv("AI_API_KEY"):   s["api_key"]  = os.getenv("AI_API_KEY")
    if os.getenv("AI_BASE_URL"):  s["base_url"] = os.getenv("AI_BASE_URL")

    # Legacy .env key fallbacks
    if not s["api_key"]:
        if s["provider"] == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
            s["api_key"] = os.getenv("ANTHROPIC_API_KEY")
        elif s["provider"] == "openai" and os.getenv("OPENAI_API_KEY"):
            s["api_key"] = os.getenv("OPENAI_API_KEY")

    # 2. settings.json wins — explicit user save always takes priority
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text())
            s.update({k: v for k, v in saved.items() if v})
        except Exception:
            pass

    return s


def save(provider: str, model: str, api_key: str, base_url: str) -> None:
    data = {
        "provider": provider,
        "model":    model,
        "api_key":  api_key,
        "base_url": base_url,
    }
    SETTINGS_FILE.write_text(json.dumps(data, indent=2))


def provider_models() -> dict:
    return {
        "anthropic": ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001"],
        "openai":    ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        "local":     ["llama3", "llama3.1", "llama3.2", "qwen2.5", "mistral", "gemma2",
                      "phi3", "deepseek-r1", "custom"],
    }
