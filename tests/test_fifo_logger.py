"""Tests for FIFO rotation and redaction in the structured logger."""

from __future__ import annotations

from pathlib import Path

from debate.observability.fifo_logger import FifoLogger


def _files(directory: Path) -> list[Path]:
    return sorted(directory.glob("debate-*.jsonl"))


def test_exceeding_line_cap_rolls_new_file(tmp_path: Path) -> None:
    logger = FifoLogger(tmp_path, max_files=10, max_lines_per_file=2)
    for i in range(5):
        logger.log("turn", index=i)
    # 5 lines / 2 per file => 3 files.
    assert len(_files(tmp_path)) == 3


def test_exceeding_file_cap_deletes_oldest(tmp_path: Path) -> None:
    logger = FifoLogger(tmp_path, max_files=2, max_lines_per_file=1)
    for i in range(5):
        logger.log("turn", index=i)
    files = _files(tmp_path)
    assert len(files) == 2
    # Only the two most recent entries survive.
    contents = "".join(p.read_text(encoding="utf-8") for p in files)
    assert '"index": 3' in contents
    assert '"index": 4' in contents
    assert '"index": 0' not in contents


def test_secret_never_written_verbatim(tmp_path: Path) -> None:
    logger = FifoLogger(tmp_path, max_files=5, max_lines_per_file=100)
    logger.log("call", api_key="sk-ant-PLAINTEXTSECRET999")
    blob = "".join(p.read_text(encoding="utf-8") for p in _files(tmp_path))
    assert "PLAINTEXTSECRET999" not in blob
    assert "[REDACTED]" in blob


def test_entries_are_json_lines(tmp_path: Path) -> None:
    import json

    logger = FifoLogger(tmp_path, max_files=5, max_lines_per_file=100)
    logger.log("hello", value=1)
    line = _files(tmp_path)[0].read_text(encoding="utf-8").strip()
    record = json.loads(line)
    assert record["event"] == "hello"
    assert record["value"] == 1
    assert "ts" in record
