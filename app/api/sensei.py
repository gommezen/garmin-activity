"""The only module that talks to Claude.

Everything Kurosawa says is a rendering of JSON the engines already produced.
`stream_voice` is the seam the API tests replace.
"""

import json
import os
from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

from app.api import persona

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        _client = AsyncAnthropic()
    return _client


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
            "content": build_user_message(register, payload, memory, question),
        }],
    ) as stream:
        async for text in stream.text_stream:
            yield text
