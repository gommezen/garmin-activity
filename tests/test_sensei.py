"""Tests for app.api.sensei — the lazy-client-construction contract.

The FastAPI app (next task) imports this module without ANTHROPIC_API_KEY
set, and its whole test suite monkeypatches stream_voice instead of hitting
the network. If client construction ever moves back to module scope, that
suite fails in a way that points nowhere near this file — so the contract is
pinned here directly.
"""

import importlib
import sys

import pytest


def _reimport_sensei():
    """Force a fresh import of app.api.sensei so module-scope code reruns."""
    sys.modules.pop("app.api.sensei", None)
    return importlib.import_module("app.api.sensei")


def test_import_succeeds_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    module = _reimport_sensei()
    assert hasattr(module, "stream_voice")


def test_get_client_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("VOICE_BASE_URL", raising=False)
    sensei = _reimport_sensei()
    with pytest.raises(RuntimeError):
        sensei._get_client()


def test_get_client_is_anthropic_by_default(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("VOICE_BASE_URL", raising=False)
    sensei = _reimport_sensei()
    from anthropic import AsyncAnthropic
    assert isinstance(sensei._get_client(), AsyncAnthropic)


def test_get_client_uses_openai_compat_when_base_url_set(monkeypatch):
    """VOICE_BASE_URL alone selects the compat path — no Anthropic key needed."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("VOICE_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("VOICE_MODEL", "gemma4:31b")
    monkeypatch.delenv("VOICE_API_KEY", raising=False)
    sensei = _reimport_sensei()
    from openai import AsyncOpenAI
    client = sensei._get_client()
    assert isinstance(client, AsyncOpenAI)
    assert str(client.base_url).startswith("http://localhost:11434/v1")


def test_get_client_raises_without_voice_model(monkeypatch):
    monkeypatch.setenv("VOICE_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.delenv("VOICE_MODEL", raising=False)
    sensei = _reimport_sensei()
    with pytest.raises(RuntimeError):
        sensei._get_client()
