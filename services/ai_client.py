"""
Unified AI client — abstracts Anthropic, OpenAI, and local OpenAI-compatible servers.

Usage:
    from services.ai_client import get_client
    client = get_client()
    text = client.complete(messages=[{"role":"user","content":"Hello"}])
"""
from __future__ import annotations
import json
from typing import Any
from services.ai_settings import load as load_settings


class AIClient:
    def __init__(self, provider: str, model: str, api_key: str, base_url: str):
        self.provider = provider
        self.model    = model
        self.api_key  = api_key
        self.base_url = base_url

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def complete(
        self,
        messages: list[dict],
        system: str = "",
        max_tokens: int = 2000,
    ) -> str:
        """Single-turn completion. Returns response text."""
        if self.provider == "anthropic":
            return self._anthropic_complete(messages, system, max_tokens)
        else:
            return self._openai_complete(messages, system, max_tokens)

    def complete_with_tools(
        self,
        messages: list[dict],
        system: str,
        tools: list[dict],
    ) -> tuple[str, list[dict]]:
        """
        Agentic tool-use loop.
        Returns (final_text, list_of_tool_results).
        `tools` should be in Anthropic format (name, description, input_schema).
        """
        if self.provider == "anthropic":
            return self._anthropic_tool_loop(messages, system, tools)
        else:
            return self._openai_tool_loop(messages, system, tools)

    def complete_with_vision(
        self,
        text_prompt: str,
        images_b64: list[str],
        system: str = "",
        max_tokens: int = 2000,
    ) -> str:
        """Vision completion — pass images as base64-encoded PNG strings."""
        if self.provider == "anthropic":
            return self._anthropic_vision(text_prompt, images_b64, system, max_tokens)
        else:
            return self._openai_vision(text_prompt, images_b64, system, max_tokens)

    def is_configured(self) -> bool:
        if self.provider == "local":
            return bool(self.base_url)
        return bool(self.api_key) and not self.api_key.startswith("your_")

    # ------------------------------------------------------------------
    # Anthropic implementation
    # ------------------------------------------------------------------

    def _anthropic_client(self):
        import anthropic
        return anthropic.Anthropic(api_key=self.api_key)

    def _anthropic_complete(self, messages, system, max_tokens):
        client = self._anthropic_client()
        kwargs = dict(model=self.model, max_tokens=max_tokens, messages=messages)
        if system:
            kwargs["system"] = system
        msg = client.messages.create(**kwargs)
        return msg.content[0].text

    def _anthropic_vision(self, text_prompt, images_b64, system, max_tokens):
        client = self._anthropic_client()
        content = []
        for img in images_b64[:4]:
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": img},
            })
        content.append({"type": "text", "text": text_prompt})
        kwargs = dict(model=self.model, max_tokens=max_tokens,
                      messages=[{"role": "user", "content": content}])
        if system:
            kwargs["system"] = system
        msg = client.messages.create(**kwargs)
        return msg.content[0].text

    def _anthropic_tool_loop(self, messages, system, tools):
        client = self._anthropic_client()
        msgs = list(messages)
        tool_results_acc = []

        for _ in range(5):
            kwargs = dict(model=self.model, max_tokens=1500,
                          tools=tools, messages=msgs)
            if system:
                kwargs["system"] = system
            resp = client.messages.create(**kwargs)

            if resp.stop_reason == "end_turn":
                text = "".join(b.text for b in resp.content if hasattr(b, "text"))
                return text, tool_results_acc

            if resp.stop_reason == "tool_use":
                tool_blocks = [b for b in resp.content if b.type == "tool_use"]
                results_msg = []
                for tb in tool_blocks:
                    result = _TOOL_EXECUTOR(tb.name, tb.input)
                    tool_results_acc.append({"tool": tb.name, "result": result})
                    results_msg.append({
                        "type": "tool_result",
                        "tool_use_id": tb.id,
                        "content": json.dumps(result),
                    })
                msgs.append({"role": "assistant", "content": resp.content})
                msgs.append({"role": "user", "content": results_msg})
                continue
            break

        text = "".join(b.text for b in resp.content if hasattr(b, "text"))
        return text or "", tool_results_acc

    # ------------------------------------------------------------------
    # OpenAI / local implementation
    # ------------------------------------------------------------------

    def _openai_client(self):
        from openai import OpenAI
        kwargs: dict[str, Any] = {"api_key": self.api_key or "local"}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return OpenAI(**kwargs)

    def _build_openai_messages(self, messages, system):
        result = []
        if system:
            result.append({"role": "system", "content": system})
        result.extend(messages)
        return result

    def _openai_complete(self, messages, system, max_tokens):
        client = self._openai_client()
        msgs = self._build_openai_messages(messages, system)
        resp = client.chat.completions.create(
            model=self.model, max_tokens=max_tokens, messages=msgs
        )
        return resp.choices[0].message.content or ""

    def _openai_vision(self, text_prompt, images_b64, system, max_tokens):
        client = self._openai_client()
        content = []
        for img in images_b64[:4]:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img}"},
            })
        content.append({"type": "text", "text": text_prompt})
        msgs = self._build_openai_messages(
            [{"role": "user", "content": content}], system
        )
        resp = client.chat.completions.create(
            model=self.model, max_tokens=max_tokens, messages=msgs
        )
        return resp.choices[0].message.content or ""

    def _openai_tool_loop(self, messages, system, tools):
        """Convert Anthropic tool format → OpenAI function format and run loop."""
        client = self._openai_client()
        oai_tools = _anthropic_tools_to_openai(tools)
        msgs = self._build_openai_messages(messages, system)
        tool_results_acc = []

        for _ in range(5):
            try:
                resp = client.chat.completions.create(
                    model=self.model, max_tokens=1500,
                    tools=oai_tools, messages=msgs,
                )
            except Exception as e:
                # Local model may not support tool calling — fall back to plain
                if "tool" in str(e).lower() or "function" in str(e).lower():
                    plain = client.chat.completions.create(
                        model=self.model, max_tokens=1500, messages=msgs
                    )
                    return plain.choices[0].message.content or "", []
                raise

            choice = resp.choices[0]
            if choice.finish_reason == "stop":
                return choice.message.content or "", tool_results_acc

            if choice.finish_reason == "tool_calls":
                tool_calls = choice.message.tool_calls or []
                msgs.append({"role": "assistant", "content": choice.message.content,
                             "tool_calls": [tc.model_dump() for tc in tool_calls]})
                for tc in tool_calls:
                    args = json.loads(tc.function.arguments or "{}")
                    result = _TOOL_EXECUTOR(tc.function.name, args)
                    tool_results_acc.append({"tool": tc.function.name, "result": result})
                    msgs.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result),
                    })
                continue
            break

        return choice.message.content or "", tool_results_acc


# ------------------------------------------------------------------
# Tool executor (injected by chat_handler to avoid circular imports)
# ------------------------------------------------------------------
_TOOL_EXECUTOR = lambda name, inputs: {"error": "Tool executor not registered"}


def register_tool_executor(fn):
    global _TOOL_EXECUTOR
    _TOOL_EXECUTOR = fn


# ------------------------------------------------------------------
# Format converters
# ------------------------------------------------------------------

def _anthropic_tools_to_openai(tools: list[dict]) -> list[dict]:
    """Convert Anthropic tool schema to OpenAI function schema."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        }
        for t in tools
    ]


# ------------------------------------------------------------------
# Factory
# ------------------------------------------------------------------

def get_client() -> AIClient:
    s = load_settings()
    return AIClient(
        provider=s["provider"],
        model=s["model"],
        api_key=s.get("api_key", ""),
        base_url=s.get("base_url", ""),
    )
