"""File exporter – append account data to a local CSV or JSON file."""
from __future__ import annotations

import csv
import dataclasses
import json
import logging
from pathlib import Path

from .base import AccountResult, ExportResult

log = logging.getLogger(__name__)

_DEFAULT_PATH = Path("output/accounts.csv")


class FileExporter:
    name = "file"

    def __init__(self, path: str | Path = _DEFAULT_PATH, fmt: str = "csv"):
        self._path = Path(path)
        self._fmt = fmt.lower()
        if self._fmt not in ("csv", "json"):
            raise ValueError(f"Unsupported format: {fmt!r} (use 'csv' or 'json')")

    def export(self, account: AccountResult) -> ExportResult:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        row = dataclasses.asdict(account)
        try:
            if self._fmt == "csv":
                self._write_csv(row)
            else:
                self._write_jsonl(row)
            log.info("File export ok -> %s", self._path)
            return ExportResult(ok=True, message=str(self._path))
        except Exception as e:
            log.error("File export failed -> %s: %s", self._path, e)
            return ExportResult(ok=False, message=str(e))

    def _write_csv(self, row: dict) -> None:
        flat = {k: (json.dumps(v) if isinstance(v, dict) else v)
                for k, v in row.items()}
        write_header = not self._path.exists() or self._path.stat().st_size == 0
        with self._path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(flat.keys()))
            if write_header:
                writer.writeheader()
            writer.writerow(flat)

    def _write_jsonl(self, row: dict) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
