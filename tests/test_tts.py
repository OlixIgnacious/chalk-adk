"""Unit tests for TTS worker, voice blend parser, and multi-provider audio generator."""

import unittest
from unittest.mock import patch, MagicMock
from src.tools.tts_worker import (
    parse_voice_blend,
    DEFAULT_GEMINI_VOICE,
    DEFAULT_KOKORO_VOICE,
)


class TestTTSWorker(unittest.TestCase):

    def test_parse_voice_blend_single(self):
        blend = parse_voice_blend("af_heart")
        self.assertEqual(blend, [("af_heart", 1.0)])

    def test_parse_voice_blend_multiple(self):
        blend = parse_voice_blend("af_heart:0.7,af_bella:0.3")
        self.assertEqual(blend, [("af_heart", 0.7), ("af_bella", 0.3)])

    def test_parse_voice_blend_plus_syntax(self):
        blend = parse_voice_blend("af_heart:0.6 + af_bella:0.4")
        self.assertEqual(blend, [("af_heart", 0.6), ("af_bella", 0.4)])

    def test_parse_voice_blend_empty_defaults(self):
        blend = parse_voice_blend("")
        self.assertEqual(len(blend), 2)
        self.assertEqual(blend[0][0], "af_heart")

    def test_default_voices(self):
        self.assertEqual(DEFAULT_GEMINI_VOICE, "Kore")
        self.assertIn("af_heart", DEFAULT_KOKORO_VOICE)


if __name__ == "__main__":
    unittest.main()

