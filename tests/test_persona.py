"""Tests for app.api.persona — prompt assembly and instruction extraction."""

from app.api import persona


class TestPrompt:
    def test_hard_rules_present(self):
        prompt = persona.SYSTEM_PROMPT.lower()
        assert "only" in prompt and "number" in prompt
        assert "one instruction" in prompt

    def test_model_is_opus_5(self):
        assert persona.MODEL == "claude-opus-5"

    def test_version_is_set(self):
        assert persona.PROMPT_VERSION


class TestRegisters:
    def test_all_four_registers(self):
        for r in ("brief", "debrief", "word", "reply"):
            assert persona.register_instruction(r)

    def test_unknown_register_raises(self):
        try:
            persona.register_instruction("nonsense")
        except ValueError:
            return
        raise AssertionError("expected ValueError")


class TestExtractInstruction:
    def test_takes_final_sentence(self):
        text = "You held the pace. Tomorrow: rest."
        assert persona.extract_instruction(text) == "Tomorrow: rest."

    def test_handles_trailing_bracket(self):
        text = "「 You held the pace. Rest tomorrow. 」"
        assert persona.extract_instruction(text) == "Rest tomorrow."

    def test_none_for_empty(self):
        assert persona.extract_instruction("") is None
        assert persona.extract_instruction("   ") is None
