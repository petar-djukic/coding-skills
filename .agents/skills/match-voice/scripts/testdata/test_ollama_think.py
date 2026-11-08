"""Offline tests for the OLLAMA_THINK setting in rewrite.generate() (GH-409).

A reasoning model whose template keeps its reasoning in `response` handed
every stage the scratchpad as the rewrite. OLLAMA_THINK is the one switch
that reaches every driver; these assert the request it produces.
"""
import json
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
SCRIPTS = os.path.normpath(os.path.join(HERE, ".."))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
import rewrite  # noqa: E402


def _fake_response(payload):
    cm = mock.MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    return cm


class OllamaThink(unittest.TestCase):
    def setUp(self):
        self.bodies = []

        def fake_urlopen(req, timeout=None):
            if req.full_url.endswith("/api/tags"):
                return _fake_response({"models": [{"name": "m"}]})
            self.bodies.append(json.loads(req.data))
            return _fake_response({"response": "text"})

        patcher = mock.patch.object(rewrite.urllib.request, "urlopen",
                                    side_effect=fake_urlopen)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _env(self, value):
        return mock.patch.dict(os.environ, {"OLLAMA_THINK": value})

    def test_unset_sends_no_field(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("OLLAMA_THINK", None)
            rewrite.generate("p", model="m")
        self.assertNotIn("think", self.bodies[-1])

    def test_an_empty_value_is_unset(self):
        with self._env(""):
            rewrite.generate("p", model="m")
        self.assertNotIn("think", self.bodies[-1])

    def test_false_and_true_spellings(self):
        for raw, want in (("false", False), ("0", False), ("off", False),
                          ("no", False), ("TRUE", True), ("1", True),
                          ("on", True), ("yes", True)):
            with self._env(raw):
                rewrite.generate("p", model="m")
            self.assertIs(self.bodies[-1]["think"], want, raw)

    def test_explicit_think_beats_the_env(self):
        """burstiness passes think=False; the env must not override it."""
        with self._env("true"):
            rewrite.generate("p", model="m", think=False)
        self.assertIs(self.bodies[-1]["think"], False)

    def test_a_typo_is_refused_before_any_request(self):
        with self._env("flase"):
            with self.assertRaisesRegex(RuntimeError, "OLLAMA_THINK"):
                rewrite.generate("p", model="m")
        self.assertEqual(self.bodies, [])

    def test_check_reports_the_setting(self):
        with self._env("false"):
            ok, msg = rewrite.check_server("http://x", "m")
        self.assertTrue(ok)
        self.assertIn("OLLAMA_THINK false", msg)
        with mock.patch.dict(os.environ):
            os.environ.pop("OLLAMA_THINK", None)
            ok, msg = rewrite.check_server("http://x", "m")
        self.assertIn("OLLAMA_THINK unset", msg)

    def test_check_refuses_a_typo(self):
        with self._env("maybe"):
            ok, msg = rewrite.check_server("http://x", "m")
        self.assertFalse(ok)
        self.assertIn("OLLAMA_THINK", msg)

    def test_cohere_ignores_the_ollama_setting(self):
        """The Ollama switch must not leak into Cohere's request body."""
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data)
            return _fake_response({"message": {"content": [
                {"type": "text", "text": "answer"}]}})

        with self._env("false"), \
                mock.patch.object(rewrite, "_cohere_key", return_value="k"), \
                mock.patch.object(rewrite.urllib.request, "urlopen",
                                  side_effect=fake_urlopen):
            rewrite.generate("p", model="cohere:command-a-03-2025")
        self.assertNotIn("think", captured["body"])


if __name__ == "__main__":
    unittest.main()
