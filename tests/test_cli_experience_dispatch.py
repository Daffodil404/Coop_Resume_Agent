from __future__ import annotations

import sys
import unittest
from contextlib import redirect_stderr
from io import StringIO
from unittest.mock import patch

from resume_agent.cli import main


class CLIExperienceDispatchTests(unittest.TestCase):
    def test_experience_ingest_uses_single_product_command(self) -> None:
        with patch.object(sys, "argv", ["resume-agent", "experience", "ingest"]):
            with patch("resume_agent.cli.run_experience_ingest", return_value=0) as ingest:
                exit_code = main()

        self.assertEqual(exit_code, 0)
        ingest.assert_called_once_with()

    def test_public_structurer_flag_is_not_exposed(self) -> None:
        stderr = StringIO()
        with patch.object(
            sys,
            "argv",
            ["resume-agent", "experience", "ingest", "--structurer", "rule_based"],
        ):
            with redirect_stderr(stderr):
                exit_code = main()

        self.assertEqual(exit_code, 2)
        self.assertIn("Usage: resume-agent [experience ingest]", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
