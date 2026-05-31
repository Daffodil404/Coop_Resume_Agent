from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from resume_agent.experience_bank.evidence import EvidenceExtractor, load_technology_keywords


class EvidenceExtractorTests(unittest.TestCase):
    def test_extracts_vite_from_default_json_dictionary(self) -> None:
        evidence = EvidenceExtractor().extract("使用 Vue 和 Vite 实现组件。")

        self.assertEqual(evidence.technologies, ["Vue", "Vite"])
        self.assertEqual(evidence.technology_lines, ["使用 Vue 和 Vite 实现组件。"])

    def test_can_load_custom_json_dictionary(self) -> None:
        with TemporaryDirectory() as temp_dir:
            dictionary_path = Path(temp_dir) / "technologies.json"
            dictionary_path.write_text(
                json.dumps({"technologies": ["CustomTool"]}),
                encoding="utf-8",
            )

            evidence = EvidenceExtractor(dictionary_path).extract("Used CustomTool for the project.")

        self.assertEqual(evidence.technologies, ["CustomTool"])

    def test_rejects_invalid_json_dictionary_shape(self) -> None:
        with TemporaryDirectory() as temp_dir:
            dictionary_path = Path(temp_dir) / "technologies.json"
            dictionary_path.write_text(json.dumps({"technologies": "Vite"}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Invalid technology keyword configuration"):
                load_technology_keywords(dictionary_path)


if __name__ == "__main__":
    unittest.main()
