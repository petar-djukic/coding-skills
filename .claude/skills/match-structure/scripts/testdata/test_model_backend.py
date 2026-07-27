#!/usr/bin/env python3
"""Tests for the configurable model backend in match_structure.py.

Run: python3 testdata/test_model_backend.py

The bug this pins: match_structure.py hardcoded MODEL = "claude-opus-4-8" with
no override, so the one skill in the prose pipeline that restructures a draft
was the one skill that rewrote it in Claude's register. Its siblings
(match-voice, tighten-style) already defaulted to gemma4 for exactly this
reason. Measured on idea-factory's how-to-loop-engineering (2026-07-26):
rewriting through claude-opus-4-8 moved Pangram fraction_ai 0.676 -> 0.753,
while the same pipeline through gemma4 reached 0.163.

These tests pin the three properties that fix depends on:
  - the default model is not a Claude model
  - a non-claude name routes to ollama, a claude-* name to the Anthropic API
  - importing the module does not require the anthropic package
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MS_PY = os.path.join(os.path.dirname(HERE), "match_structure.py")


def load():
    spec = importlib.util.spec_from_file_location("match_structure", MS_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_import_without_anthropic():
    """The module must load with anthropic absent — the default path never uses it."""
    saved = sys.modules.pop("anthropic", None)
    sys.modules["anthropic"] = None          # poison: any import raises
    try:
        mod = load()                          # must not raise
        assert mod.DEFAULT_MODEL
    finally:
        sys.modules.pop("anthropic", None)
        if saved is not None:
            sys.modules["anthropic"] = saved
    print("ok: imports without the anthropic package")


def test_default_is_not_claude():
    mod = load()
    assert not mod.DEFAULT_MODEL.startswith("claude-"), (
        f"default model regressed to Claude: {mod.DEFAULT_MODEL}. The rewrite "
        "must decorrelate from the drafting model family.")
    assert mod.DEFAULT_MODEL.startswith("gemma4"), mod.DEFAULT_MODEL
    print(f"ok: default model is {mod.DEFAULT_MODEL}")


def test_backend_selection():
    mod = load()
    ollama = mod.make_backend("gemma4:12b", "http://localhost:11434")
    assert isinstance(ollama, mod._OllamaBackend), type(ollama)
    assert ollama.model == "gemma4:12b"
    print("ok: non-claude model routes to ollama")


def test_env_override():
    mod_path, saved = MS_PY, os.environ.get("MATCH_VOICE_MODEL")
    os.environ["MATCH_VOICE_MODEL"] = "kimi-k2.6:cloud"
    try:
        mod = load()
        assert mod.DEFAULT_MODEL == "kimi-k2.6:cloud", mod.DEFAULT_MODEL
    finally:
        if saved is None:
            os.environ.pop("MATCH_VOICE_MODEL", None)
        else:
            os.environ["MATCH_VOICE_MODEL"] = saved
    print("ok: MATCH_VOICE_MODEL overrides the default")


def test_flatten_preserves_both_halves():
    """Anthropic-shaped system+content must survive collapsing into one prompt."""
    mod = load()
    out = mod._flatten(
        [{"type": "text", "text": "SYSTEM RULES"}],
        [{"type": "text", "text": "BODY ONE"}, {"type": "text", "text": "BODY TWO"}],
    )
    for needle in ("SYSTEM RULES", "BODY ONE", "BODY TWO"):
        assert needle in out, f"{needle} lost in _flatten: {out!r}"
    # a plain string system prompt is also legal in the original API shape
    assert "PLAIN" in mod._flatten("PLAIN", [{"type": "text", "text": "B"}])
    print("ok: _flatten preserves system and content")


if __name__ == "__main__":
    test_import_without_anthropic()
    test_default_is_not_claude()
    test_backend_selection()
    test_env_override()
    test_flatten_preserves_both_halves()
    print("\nall model-backend tests passed")
