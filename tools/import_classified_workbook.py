"""Convert the authoritative classified workbook into the JSON master seed.

The actual reading lives in ``src/etl/excel.py`` so that this offline tool, the
admin upload endpoint, and ``scripts/kelola_database.py excel`` all share one
converter. This file is only the thin file-in/file-out wrapper.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.etl.excel import baca_workbook  # noqa: E402


def main(source: Path, target: Path) -> None:
    sumber = baca_workbook(source.read_bytes(), source.name)
    target.write_text(json.dumps(sumber, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
