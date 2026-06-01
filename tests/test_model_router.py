from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml

from resume_agent.ai.model_router import ModelRouterError, get_model_config


class ModelRouterTests(unittest.TestCase):
    def test_resolves_default_model_config_for_jd_analysis(self) -> None:
        config = get_model_config("jd_analysis")

        self.assertEqual(config.task_key, "jd_analysis")
        self.assertEqual(config.model, "gpt-4.1-mini")
        self.assertEqual(config.temperature, 0.1)
        self.assertEqual(config.max_output_tokens, 1500)

    def test_resolves_default_model_config_for_cover_letter_writer(self) -> None:
        config = get_model_config("cover_letter_writer")

        self.assertEqual(config.model, "gpt-5.4")
        self.assertEqual(config.temperature, 0.35)
        self.assertEqual(config.max_output_tokens, 1800)

    def test_environment_variable_override_wins(self) -> None:
        with patch.dict(os.environ, {"OPENAI_COVER_LETTER_WRITER_MODEL": "gpt-test-writer"}, clear=False):
            config = get_model_config("cover_letter_writer")

        self.assertEqual(config.model, "gpt-test-writer")

    def test_unknown_task_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(ModelRouterError, "Unknown model-routing task key"):
            get_model_config("not_a_task")

    def test_loads_private_config_aliases_from_data_root(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_root = Path(temp_dir)
            config_path = data_root / "data/private/config.yaml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                yaml.safe_dump(
                    {
                        "ai": {
                            "models": {"balanced": "gpt-custom-mini"},
                            "tasks": {"jd_analysis": {"model": "balanced", "max_output_tokens": 2222}},
                        }
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            config = get_model_config("jd_analysis", data_root=data_root)

        self.assertEqual(config.model, "gpt-custom-mini")
        self.assertEqual(config.max_output_tokens, 2222)


if __name__ == "__main__":
    unittest.main()
