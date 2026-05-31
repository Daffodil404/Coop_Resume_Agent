from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from resume_agent.experience_bank.evidence import (
    EvidenceExtractor,
    load_technology_keywords,
    normalize_technology_evidence_text,
    split_supported_compound_technology,
    technology_is_explicitly_mentioned,
)


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

    def test_extracts_figma_and_mcp_separately_from_mixed_language_evidence(self) -> None:
        raw_line = "使用了 Figma 的 MCP 来完成样式实现。"
        evidence = EvidenceExtractor().extract(raw_line)

        self.assertEqual(evidence.technologies, ["Figma", "MCP"])
        self.assertEqual(evidence.technology_lines, [raw_line])

    def test_normalization_supports_individual_terms_but_not_combined_figma_mcp(self) -> None:
        raw_line = "使用了 Figma 的 MCP 来完成样式实现。"

        self.assertEqual(
            normalize_technology_evidence_text(raw_line),
            "使用了 figma 的 mcp 来完成样式实现。",
        )
        self.assertTrue(technology_is_explicitly_mentioned("Figma", raw_line))
        self.assertTrue(technology_is_explicitly_mentioned("MCP", raw_line))
        self.assertFalse(technology_is_explicitly_mentioned("Figma MCP", raw_line))

    def test_splits_supported_compound_technology_into_confirmed_parts(self) -> None:
        split = split_supported_compound_technology("Figma MCP", ["Figma", "MCP"])

        self.assertEqual(split, ["Figma", "MCP"])

    def test_rejects_invalid_json_dictionary_shape(self) -> None:
        with TemporaryDirectory() as temp_dir:
            dictionary_path = Path(temp_dir) / "technologies.json"
            dictionary_path.write_text(json.dumps({"technologies": "Vite"}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Invalid technology keyword configuration"):
                load_technology_keywords(dictionary_path)


if __name__ == "__main__":
    unittest.main()
