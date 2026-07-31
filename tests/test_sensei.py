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
    sensei = _reimport_sensei()
    with pytest.raises(RuntimeError):
        sensei._get_client()
