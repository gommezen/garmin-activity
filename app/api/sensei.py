"""The only module that talks to the language model.

Everything Kurosawa says is a rendering of JSON the engines already produced.
`stream_voice` is the seam the API tests replace.

Two backends, chosen by env: Anthropic by default; any OpenAI-compatible
endpoint (Ollama, Moonshot/Kimi, NIM) when VOICE_BASE_URL is set, with
VOICE_MODEL naming the model and VOICE_API_KEY the key ("ollama" locally).
"""

import json
import os
from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.api import persona

_client: AsyncAnthropic | AsyncOpenAI | None = None


def _get_client() -> AsyncAnthropic | AsyncOpenAI:
    global _client
    if _client is None:
        base_url = os.getenv("VOICE_BASE_URL")
        if base_url:
            if not os.getenv("VOICE_MODEL"):
                raise RuntimeError("VOICE_MODEL is not set (required with VOICE_BASE_URL)")
            _client = AsyncOpenAI(base_url=base_url,
                                  api_key=os.getenv("VOICE_API_KEY", "ollama"))
        else:
            if not os.getenv("ANTHROPIC_API_KEY"):
                raise RuntimeError("ANTHROPIC_API_KEY is not set")
            _client = AsyncAnthropic()
    return _client


def active_model() -> str:
    """The model identifier dialogue is actually generated with.

    Persisted as provenance in the insert-only tables — must follow the
    backend selection in `_get_client`, never a constant.
    """
    if os.getenv("VOICE_BASE_URL"):
        return os.environ["VOICE_MODEL"]
    return persona.MODEL


def build_user_message(register: str, payload: dict, memory: list[str],
                       question: str | None) -> str:
    parts = [persona.register_instruction(register), "", json.dumps(payload, indent=2)]
    if memory:
        parts += ["", "What you last told this student, newest first:"]
        parts += [f"- {m}" for m in memory]
    if question:
        parts += ["", f"Their question: {question}"]
    return "\n".join(parts)


async def stream_voice(register: str, payload: dict, memory: list[str],
                       question: str | None = None) -> AsyncIterator[str]:
    """Yield Kurosawa's words as they arrive."""
    client = _get_client()
    message = build_user_message(register, payload, memory, question)
    if isinstance(client, AsyncOpenAI):
        # Thinking models (gemma4, deepseek-r1, qwen3, ornith) spend tokens on
        # a reasoning field before any content; 1000 starves them into silence.
        # VOICE_REASONING_EFFORT=none turns thinking off on Ollama — only sent
        # when set, so backends that reject the field stay usable.
        extra = {}
        if effort := os.getenv("VOICE_REASONING_EFFORT"):
            extra["reasoning_effort"] = effort
        stream = await client.chat.completions.create(
            model=os.environ["VOICE_MODEL"],
            max_tokens=4000,
            stream=True,
            **extra,
            messages=[
                {"role": "system", "content": persona.SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
        return
    async with client.messages.stream(
        model=persona.MODEL,
        max_tokens=1000,
        output_config={"effort": "low"},
        system=[{
            "type": "text",
            "text": persona.SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": message,
        }],
    ) as stream:
        async for text in stream.text_stream:
            yield text
