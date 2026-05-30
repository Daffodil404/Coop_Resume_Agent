from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from resume_agent.storage import (
    build_application_folder_name,
    create_application_dir,
    create_application_metadata,
    save_application_artifacts,
)


class StorageTests(unittest.TestCase):
    def test_build_application_folder_name_uses_date_company_and_role(self) -> None:
        created_at = datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc)

        folder_name = build_application_folder_name(
            company="Test Company",
            role_title="Software Engineer Co-op",
            created_at=created_at,
        )

        self.assertEqual(
            folder_name,
            "2026-05-30_test_company_software_engineer_co_op",
        )

    def test_create_application_metadata_has_required_fields(self) -> None:
        created_at = datetime(2026, 5, 30, 12, 15, tzinfo=timezone.utc)
        analysis = {
            "company": "Test Company",
            "role_title": "Software Engineer Co-op",
        }

        metadata = create_application_metadata(
            application_dir=Path("/tmp/2026-05-30_test_company_software_engineer_co_op"),
            analysis=analysis,
            created_at=created_at,
        )

        self.assertEqual(
            metadata["application_id"],
            "2026-05-30_test_company_software_engineer_co_op",
        )
        self.assertEqual(metadata["company"], "Test Company")
        self.assertEqual(metadata["role_title"], "Software Engineer Co-op")
        self.assertEqual(metadata["created_at"], "2026-05-30T12:15:00Z")
        self.assertEqual(metadata["source"], "interactive_cli")
        self.assertEqual(metadata["status"], "draft")

    def test_create_application_dir_appends_suffix_on_collision(self) -> None:
        created_at = datetime(2026, 5, 30, 12, 0, tzinfo=timezone.utc)
        with TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            first = create_application_dir(
                output_root=output_root,
                company="Test Company",
                role_title="Software Engineer Co-op",
                created_at=created_at,
            )
            second = create_application_dir(
                output_root=output_root,
                company="Test Company",
                role_title="Software Engineer Co-op",
                created_at=created_at,
            )
            third = create_application_dir(
                output_root=output_root,
                company="Test Company",
                role_title="Software Engineer Co-op",
                created_at=created_at,
            )

        self.assertEqual(first.name, "2026-05-30_test_company_software_engineer_co_op")
        self.assertEqual(second.name, "2026-05-30_test_company_software_engineer_co_op_2")
        self.assertEqual(third.name, "2026-05-30_test_company_software_engineer_co_op_3")

    def test_save_application_artifacts_writes_required_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            application_dir = Path(temp_dir)
            save_application_artifacts(
                application_dir=application_dir,
                raw_jd="raw jd",
                clean_jd="clean jd",
                analysis={"company": "Test Company"},
                metadata={"application_id": "test-application"},
            )

            self.assertEqual((application_dir / "jd_raw.txt").read_text(), "raw jd")
            self.assertEqual((application_dir / "jd_clean.txt").read_text(), "clean jd")
            self.assertTrue((application_dir / "jd_analysis.json").is_file())
            self.assertTrue((application_dir / "metadata.json").is_file())


if __name__ == "__main__":
    unittest.main()
