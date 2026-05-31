from __future__ import annotations

import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import patch

from resume_agent.cli import main


class CLIInterruptTests(unittest.TestCase):
    def test_ctrl_c_during_jd_input_cancels_without_traceback(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        interrupted_stdin = StringIO()
        with patch.object(interrupted_stdin, "read", side_effect=KeyboardInterrupt):
            with patch.object(sys, "argv", ["resume-agent"]):
                with patch.object(sys, "stdin", interrupted_stdin):
                    with redirect_stdout(stdout):
                        with redirect_stderr(stderr):
                            exit_code = main()

        self.assertEqual(exit_code, 130)
        self.assertIn("Job description ingestion cancelled.", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
