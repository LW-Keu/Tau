import importlib.util
import os
import time
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "memory" / "L4_raw_sessions" / "compress_session.py"
SPEC = importlib.util.spec_from_file_location("compress_session", MODULE_PATH)
compress_session = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compress_session)


def _batch(candidate, tmp_path):
    now = time.time()
    os.utime(candidate, (now - 10_800, now - 10_800))
    retained = []
    for index in range(10):
        path = tmp_path / f"model_responses_recent_{index}.txt"
        path.write_text("active", encoding="utf-8")
        os.utime(path, (now + index, now + index))
        retained.append(path)
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    report = compress_session.batch_process(
        [str(candidate), *(str(path) for path in retained)],
        l4_dir=str(archive_dir),
        dry_run=False,
    )
    return archive_dir, report


def test_batch_keeps_skipped_input(tmp_path):
    candidate = tmp_path / "model_responses_skipped.txt"
    candidate.write_text("no timestamp", encoding="utf-8")

    _, report = _batch(candidate, tmp_path)

    assert candidate.exists()
    assert report["skipped"] == 1
    assert report["deleted_raw"] == 0


def test_batch_keeps_failed_input(tmp_path):
    candidate = tmp_path / "model_responses_failed.txt"
    candidate.mkdir()

    _, report = _batch(candidate, tmp_path)

    assert candidate.exists()
    assert report["errors"] == 1
    assert report["deleted_raw"] == 0


def test_batch_deletes_only_verified_archived_input(tmp_path):
    candidate = tmp_path / "model_responses_archived.txt"
    candidate.write_text(
        "=== Prompt === 2026-07-01 12:00:00\n" + "payload\n" * 1000,
        encoding="utf-8",
    )

    archive_dir, report = _batch(candidate, tmp_path)

    archive = archive_dir / "2026-07.zip"
    with zipfile.ZipFile(archive) as zipped:
        assert "0701_1200-0701_1200.txt" in zipped.namelist()
    assert not candidate.exists()
    assert report["processed"] == 1
    assert report["deleted_raw"] == 1
