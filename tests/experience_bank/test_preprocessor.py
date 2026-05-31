from __future__ import annotations

import unittest

from resume_agent.experience_bank.preprocessor import RawNotePreprocessor


class RawNotePreprocessorTests(unittest.TestCase):
    def test_normalizes_line_endings_whitespace_and_blank_lines(self) -> None:
        clean_note = RawNotePreprocessor().preprocess(" Title:  Sample \r\n\r\n\r\n Built   API. \r")

        self.assertEqual(clean_note, "Title: Sample\n\nBuilt API.")


if __name__ == "__main__":
    unittest.main()
