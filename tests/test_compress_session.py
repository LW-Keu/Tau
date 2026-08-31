import importlib.util
import os
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "memories" / "L4_raw_sessions" / "compress_session.py"
SPEC = importlib.util.spec_from_file_location("compress_session", MODULE_PATH)
compress_session = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compress_session)


class CompressSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _batch(self, candidates):
        if isinstance(candidates, Path):
            candidates = [candidates]
        now = time.time()
        for candidate in candidates:
            os.utime(candidate, (now - 10_800, now - 10_800))
        retained = []
        for index in range(10):
            path = self.root / f"model_responses_recent_{index}.txt"
            path.write_text("active", encoding="utf-8")
            os.utime(path, (now + index, now + index))
            retained.append(path)
        archive_dir = self.root / "archive"
        archive_dir.mkdir()
        report = compress_session.batch_process(
            [*(str(path) for path in candidates), *(str(path) for path in retained)],
            l4_dir=str(archive_dir),
            dry_run=False,
        )
        return archive_dir, report

    def test_batch_keeps_skipped_input(self):
        candidate = self.root / "model_responses_skipped.txt"
        candidate.write_text("no timestamp", encoding="utf-8")

        _, report = self._batch(candidate)

        self.assertTrue(candidate.exists())
        self.assertEqual(report["skipped"], 1)
        self.assertEqual(report["deleted_raw"], 0)

    def test_batch_keeps_failed_input(self):
        candidate = self.root / "model_responses_failed.txt"
        candidate.mkdir()

        _, report = self._batch(candidate)

        self.assertTrue(candidate.exists())
        self.assertEqual(report["errors"], 1)
        self.assertEqual(report["deleted_raw"], 0)

    def test_batch_deletes_only_verified_archived_input(self):
        candidate = self.root / "model_responses_archived.txt"
        candidate.write_text(
            "=== Prompt === 2026-07-01 12:00:00\n" + "payload\n" * 1000,
            encoding="utf-8",
        )

        archive_dir, report = self._batch(candidate)

        archive = archive_dir / "2026-07.zip"
        with zipfile.ZipFile(archive) as zipped:
            self.assertIn("0701_1200-0701_1200.txt", zipped.namelist())
        self.assertFalse(candidate.exists())
        self.assertEqual(report["processed"], 1)
        self.assertEqual(report["deleted_raw"], 1)

    def test_batch_preserves_conflicting_source_and_unique_zip_member(self):
        first = self.root / "model_responses_first.txt"
        second = self.root / "model_responses_second.txt"
        history = "<history>[USER] hello\\n[Agent] reply</history>\n"
        first.write_text(
            "=== Prompt === 2026-07-01 12:00:00\nfirst\n"
            + history + "first payload\n" * 1000,
            encoding="utf-8",
        )
        second.write_text(
            "=== Prompt === 2026-07-01 12:00:30\nsecond\n"
            + history + "second payload\n" * 1000,
            encoding="utf-8",
        )

        archive_dir, report = self._batch([first, second])

        with zipfile.ZipFile(archive_dir / "2026-07.zip") as zipped:
            members = zipped.namelist()
            self.assertEqual(members.count("0701_1200-0701_1200.txt"), 1)
            self.assertIn(b"first payload", zipped.read(members[0]))
        self.assertFalse(first.exists())
        self.assertTrue(second.exists())
        self.assertEqual(report["deleted_raw"], 1)
        self.assertEqual(report["skipped"], 1)
        histories = (archive_dir / "all_histories.txt").read_text(encoding="utf-8")
        self.assertEqual(histories.count("SESSION: 0701_1200-0701_1200"), 1)

    def test_batch_does_not_append_history_before_archive_succeeds(self):
        candidate = self.root / "model_responses_archived.txt"
        candidate.write_text(
            "=== Prompt === 2026-07-01 12:00:00\n"
            "<history>[USER] hello\\n[Agent] reply</history>\n"
            + "payload\n" * 1000,
            encoding="utf-8",
        )

        with mock.patch.object(
            compress_session.zipfile, "ZipFile", side_effect=OSError("archive failed")
        ):
            with self.assertRaisesRegex(OSError, "archive failed"):
                self._batch(candidate)

        self.assertTrue(candidate.exists())
        history_path = self.root / "archive" / "all_histories.txt"
        self.assertFalse(history_path.exists())


if __name__ == "__main__":
    unittest.main()
