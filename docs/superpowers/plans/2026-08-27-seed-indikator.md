# Auto-seed Indikator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a fresh SEBATIK deploy self-populate the 86-row indicator
catalog (+ metadata + baseline provincial realisasi/target values) exactly
once, automatically, with zero manual steps — while never touching an
already-populated database on redeploy.

**Architecture:** A one-time export script converts the authoritative Excel
workbook into a committed JSON fixture. A new idempotent CLI subcommand
(`python -m backend.app.cli seed-indikator`) reads that fixture and bulk-inserts
it into the database, but only if the `indikator` table is currently empty.
`docker-entrypoint.sh` calls this subcommand once, right after the existing
`alembic upgrade head` step, before the web server starts.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (ORM), Alembic (schema
only — **no new migration in this plan**), openpyxl (already a dependency,
do not add new packages), pytest, ruff, mypy.

## Global Constraints

These apply to every task below. Re-read this section before each task.

- **Language convention (this repo only):** All code comments and commit
  messages are in **Indonesian** (Bahasa Indonesia). Function/variable names
  on new/modified backend modules are Indonesian words (e.g. `jumlah`,
  `seed_massal`, `berkas`), matching every existing file you will touch.
  Do not introduce English identifiers into these files.
- **No new dependencies.** `openpyxl>=3.1,<4` is already in
  `requirements.txt` — that is the only library you need for reading Excel.
  Do not add `pandas` or anything else.
- **Layering rule (backend/app/):** This repo enforces `routers -> services
  -> repositories -> models` as a hard rule, checked by
  `tests/unit/test_arsitektur.py` (AST-based, not just convention). Concretely:
  - Raw SQL (`text("...")`) is banned outside `backend/app/repositories/`.
  - Routers may not call `select()`/`insert()`/`update()`/`delete()`/`execute()`
    directly — only repositories may.
  - This plan does not touch any router, but the same discipline still
    applies to `backend/app/cli.py`: it must call repository functions for
    all database access, never construct SQLAlchemy queries itself. Treat
    `cli.py` as if it were a service — orchestration only.
- **No schema changes.** The `indikator`, `metadata_indikator`, and
  `nilai_indikator` tables already exist (from
  `backend/alembic/versions/0001_baseline_skema_konsolidasi.py`). This plan
  adds **zero** new Alembic migrations. If at any point you think you need a
  migration, stop — that means something in this plan was misunderstood.
- **Do not seed on import.** `tests/unit/test_arsitektur.py::test_database_tidak_punya_efek_samping_impor`
  asserts that no seed/migration logic runs when a module is imported. All
  new seeding code must only run when explicitly invoked (a CLI subcommand
  call), never at module import time.
- **Verification commands** (run from repo root unless noted):
  - `python -m pytest` — full backend test suite.
  - `python -m pytest tests/integrasi/test_cli.py -v` — this plan's tests specifically.
  - `ruff check .` and `ruff format --check .` — lint/format, must be clean.
  - `mypy backend src` — type check, must be clean.
- **The source Excel file** is expected at
  `data/raw/BASIS_DATA_INDIKATOR_ISV-IUP_KALTARA.xlsx`. This directory is
  **not tracked by git** (see repo `CLAUDE.md`: `data/raw/`, `data/processed/`
  are gitignored, copied locally from an office file share). If this file is
  missing when you reach Task 3, **stop and tell the user** — do not invent
  or fabricate indicator data to make progress.

---

### Task 1: Repository helpers — count and bulk-insert

**Files:**
- Modify: `backend/app/repositories/indikator.py`
- Test: `tests/integrasi/test_repository_indikator_seed.py` (new)

**Interfaces:**
- Consumes: `backend.app.models.Indikator`, `MetadataIndikator`, `NilaiIndikator`
  (all already exist in `backend/app/models/indikator.py`); the `session`
  pytest fixture from `tests/conftest.py` (function-scoped, rolled back after
  each test, schema built by Alembic).
- Produces: `repo_indikator.jumlah(session: Session) -> int` and
  `repo_indikator.seed_massal(session: Session, indikator: list[dict],
  metadata: list[dict], nilai: list[dict]) -> None`. Task 4 (the CLI
  subcommand) calls both of these by exact name.

**Context you need:** Open `backend/app/repositories/indikator.py` and look
at the top of the file — it already imports
`from ..models import Indikator, MetadataIndikator, StatusVerifikasi` and
`from sqlalchemy import Select, asc, desc, func, select`. You need to add
`NilaiIndikator` to the models import and `insert` to the sqlalchemy import.

The existing file already has small standalone query functions like this one
(for reference, don't change it):

```python
def ada(session: Session, id_indikator: str) -> bool:
    stmt = select(Indikator.id_indikator).where(Indikator.id_indikator == id_indikator)
    return session.scalars(stmt).first() is not None
```

You're adding two functions in the same style, near the top of the file
(right after `ada`).

- [ ] **Step 1: Write the failing tests**

Create `tests/integrasi/test_repository_indikator_seed.py`:

```python
"""Tes repository.indikator: hitung baris dan insert massal untuk seed."""

from __future__ import annotations

from backend.app.repositories import indikator as repo_indikator


def test_jumlah_nol_saat_tabel_kosong(session):
    assert repo_indikator.jumlah(session) == 0


def test_jumlah_menghitung_baris_yang_ada(session):
    from backend.app.models import Indikator

    session.add(Indikator(id_indikator="ISV-001", kategori="ISV", nomor=1, nama_indikator="Contoh"))
    session.flush()

    assert repo_indikator.jumlah(session) == 1


def test_seed_massal_insert_ke_tiga_tabel(session):
    from backend.app.models import Indikator, MetadataIndikator, NilaiIndikator

    repo_indikator.seed_massal(
        session,
        indikator=[{"id_indikator": "ISV-001", "kategori": "ISV", "nomor": 1, "nama_indikator": "Contoh"}],
        metadata=[{"id_indikator": "ISV-001", "definisi": "Definisi contoh"}],
        nilai=[
            {
                "id_indikator": "ISV-001",
                "wilayah_kode": "65",
                "tahun": 2021,
                "jenis": "realisasi",
                "nilai": 100.0,
            }
        ],
    )
    session.flush()

    assert session.get(Indikator, "ISV-001") is not None
    assert session.get(MetadataIndikator, "ISV-001").definisi == "Definisi contoh"
    baris_nilai = session.query(NilaiIndikator).filter_by(id_indikator="ISV-001").one()
    assert baris_nilai.tahun == 2021
    assert baris_nilai.jenis == "realisasi"
```

Notes on this test:
- `wilayah_kode="65"` works without creating a `Wilayah` row yourself —
  `backend/alembic/versions/0002_seed_wilayah.py` already inserts code `"65"`
  as part of the `alembic upgrade head` that builds the test schema (see the
  `session` fixture in `tests/conftest.py`).
- `session` is a pytest fixture already defined in `tests/conftest.py` at
  the repo root — you don't need to create it, just use it as a test
  parameter name and pytest will inject it.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/integrasi/test_repository_indikator_seed.py -v`

Expected: FAIL — `AttributeError: module 'backend.app.repositories.indikator'
has no attribute 'jumlah'` (or similar `ImportError`/`AttributeError` for
`seed_massal`).

- [ ] **Step 3: Implement the two repository functions**

Open `backend/app/repositories/indikator.py`. Change the import block at the
top from:

```python
from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.orm import Session

from ..models import Indikator, MetadataIndikator, StatusVerifikasi
```

to:

```python
from sqlalchemy import Select, asc, desc, func, insert, select
from sqlalchemy.orm import Session

from ..models import Indikator, MetadataIndikator, NilaiIndikator, StatusVerifikasi
```

Then add these two functions right after the existing `ada()` function
(after its `return` line, before the blank line that precedes `_saring`):

```python
def jumlah(session: Session) -> int:
    """Jumlah baris `indikator`. Dipakai CLI untuk cek idempotensi seed awal."""
    return session.scalar(select(func.count()).select_from(Indikator)) or 0


def seed_massal(
    session: Session,
    indikator: list[dict],
    metadata: list[dict],
    nilai: list[dict],
) -> None:
    """Insert massal indikator+metadata+nilai dari fixture seed awal.

    Urutan tabel penting: `metadata_indikator` dan `nilai_indikator` punya FK
    ke `indikator.id_indikator`, jadi `indikator` harus masuk lebih dulu.
    Tidak melakukan commit — pemanggil (CLI) yang memutuskan kapan commit,
    sama seperti pola `seed_akun`/`pastikan_wilayah` di `cli.py`.
    """
    if indikator:
        session.execute(insert(Indikator), indikator)
    if metadata:
        session.execute(insert(MetadataIndikator), metadata)
    if nilai:
        session.execute(insert(NilaiIndikator), nilai)
```

Type annotations use plain `list[dict]` (not `list[dict[str, Any]]`) only if
the rest of the file does the same — check: this file's existing functions
use `Sequence[str] | None` style annotations, so match that precision. Use
`list[dict[str, object]]` for both parameters and update the signature to:

```python
def seed_massal(
    session: Session,
    indikator: list[dict[str, object]],
    metadata: list[dict[str, object]],
    nilai: list[dict[str, object]],
) -> None:
```

(This keeps `mypy backend src` clean — a bare `dict` without type args is
flagged by strict mypy configs.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/integrasi/test_repository_indikator_seed.py -v`
Expected: 3 passed.

- [ ] **Step 5: Lint and type-check**

Run: `ruff check backend/app/repositories/indikator.py tests/integrasi/test_repository_indikator_seed.py`
Expected: no output (clean).

Run: `ruff format --check backend/app/repositories/indikator.py`
Expected: no output (already formatted correctly — if it complains, run
`ruff format backend/app/repositories/indikator.py` and re-check).

Run: `mypy backend/app/repositories/indikator.py`
Expected: `Success: no issues found`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/repositories/indikator.py tests/integrasi/test_repository_indikator_seed.py
git commit -m "$(cat <<'EOF'
Tambah jumlah() dan seed_massal() di repository indikator

Dipakai perintah CLI seed-indikator (task berikutnya) untuk cek
idempotensi dan insert massal dari fixture JSON.
EOF
)"
```

---

### Task 2: Export script — Excel klasifikasi → JSON fixture

**Files:**
- Create: `scripts/ekspor_seed_indikator.py`
- Test: `tests/unit/test_ekspor_seed_indikator.py` (new)

**Interfaces:**
- Consumes: `src.etl.common.clean_text`, `src.etl.common.parse_angka` (already
  exist, do not modify — see `src/etl/common.py`), `src.etl.transform.proxy.ekstrak_proxy`
  (already exists — see `src/etl/transform/proxy.py`, signature
  `ekstrak_proxy(penanda: Any, catatan: Any) -> tuple[int, str | None]`).
- Produces: two importable functions,
  `baca_indikator_dan_metadata(wb) -> tuple[list[dict], list[dict]]` and
  `baca_nilai(wb) -> list[dict]`, both taking an `openpyxl.Workbook`-like
  object. Task 3 imports these two functions from
  `scripts.ekspor_seed_indikator` and calls `main(sumber_path, target_path)`.

**Context you need — why this file's mapping logic looks the way it does:**

The source workbook (`data/raw/BASIS_DATA_INDIKATOR_ISV-IUP_KALTARA.xlsx`)
has two sheets you care about:

1. **`"Basis Data Indikator"`** — one row per indicator (86 rows), columns
   (exact header text, row 1 of the sheet) include: `ID Indikator`,
   `Kategori`, `Kelompok / Pilar`, `Arah Pembangunan`, `Kode Indikator`,
   `Nama Indikator (RPJPD Provinsi / dipakai Kaltara)`, `Indikator Proxy?`,
   `Definisi (RPJPD Provinsi)`, `Rumus Perhitungan (RPJPD Provinsi)`,
   `Interpretasi (RPJPD Provinsi)`, `Sumber Data (RPJPD Provinsi)`,
   `Frekuensi (RPJPD Provinsi)`, `Status Metadata`,
   `Perangkat Daerah Pengampu (Kaltara)`, `Ketersediaan Data`,
   `Periode Data`, `Tahun Data Terakhir`, then several `Realisasi 20XX` /
   `Target 20XX` columns (ignore these — sheet 2 below is the clean source
   for values), then `Catatan Kualitas Data`, `Keterangan (Rakor Kaltara)`,
   `Keterangan RPJMD / Catatan Kaltara`.

2. **`"Data Target-Realisasi"`** — one row per (indicator, year, jenis) —
   660 non-empty rows, no duplicate `(ID Indikator, Tahun, Jenis Nilai)` keys
   (already verified during design). Columns: `ID Indikator`, `Kategori`,
   `Kelompok / Pilar`, `Kode Indikator`, `Nama Indikator (Kaltara)`,
   `Jenis Nilai` (values are exactly `"Realisasi"` or `"Target"`), `Tahun`,
   `Nilai (Angka)`, `Nilai (Teks Asli)`, `Satuan/Catatan`.

**Critical, easy-to-miss detail:** the `"Arah Pembangunan"` column in sheet 1
means **two different things** depending on `Kategori`:
- For `ISV` rows, its value is a development-direction sentence (e.g.
  "Peningkatan Pendapatan per Kapita") → maps to the model column
  `indikator.arah_pembangunan`.
- For `IUP` rows, its value is an "Arah Indonesia Emas" pillar code (e.g.
  "IE1 - Kesehatan untuk Semua") → maps to a **different** model column,
  `indikator.arah_ie`.

This was confirmed by cross-checking `tests/api/conftest.py` fixtures against
the real workbook data during design — do not "fix" this into a single
column, it is correct as described.

**Another detail:** the production `id_indikator` format is 3-digit zero
padded (`ISV-001`, `IUP-050`) — read directly from the `"ID Indikator"`
column, do not compute it. There is an existing function
`src/etl/common.py::indicator_id()` that produces a **2-digit** format
(`ISV-04`) — that is for a *different*, legacy workbook shape
(`"form provinsi"` sheet, used by `src/etl/extract/master.py`). **Do not use
`indicator_id()` in this script.** Derive `nomor` (the model's integer
sequence-within-category column) by parsing the numeric suffix already
present in `"ID Indikator"` instead.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_ekspor_seed_indikator.py`:

```python
"""Tes fungsi pembacaan Excel klasifikasi -> dict siap-seed.

Memakai workbook in-memory (bukan file di disk) supaya cepat dan tidak
bergantung pada data/raw/ yang tidak ter-commit.
"""

from __future__ import annotations

from openpyxl import Workbook

from scripts.ekspor_seed_indikator import baca_indikator_dan_metadata, baca_nilai

HEADER_INDIKATOR = [
    "ID Indikator",
    "Kategori",
    "Kelompok / Pilar",
    "Arah Pembangunan",
    "Kode Indikator",
    "Nama Indikator (RPJPD Provinsi / dipakai Kaltara)",
    "Indikator Proxy?",
    "Definisi (RPJPD Provinsi)",
    "Rumus Perhitungan (RPJPD Provinsi)",
    "Interpretasi (RPJPD Provinsi)",
    "Sumber Data (RPJPD Provinsi)",
    "Frekuensi (RPJPD Provinsi)",
    "Status Metadata",
    "Perangkat Daerah Pengampu (Kaltara)",
    "Ketersediaan Data",
    "Periode Data",
    "Tahun Data Terakhir",
    "Catatan Kualitas Data",
    "Keterangan (Rakor Kaltara)",
    "Keterangan RPJMD / Catatan Kaltara",
]


def _wb_indikator(baris: list[list]) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Basis Data Indikator"
    ws.append(HEADER_INDIKATOR)
    for satu in baris:
        ws.append(satu)
    return wb


def test_arah_pembangunan_untuk_isv_arah_ie_untuk_iup():
    wb = _wb_indikator(
        [
            [
                "ISV-001", "ISV", "Sasaran Visi", "Peningkatan Pendapatan per Kapita", "1",
                "PDRB per Kapita", "Tidak", "def isv", "rumus isv", "interp isv",
                "BPS", "Tahunan", "Lengkap", "BPS", "Tersedia", "Tahunan", 2025,
                None, None, None,
            ],
            [
                "IUP-001", "IUP", "Transformasi Sosial", "IE1 - Kesehatan untuk Semua", "1",
                "Usia Harapan Hidup", "Tidak", "def iup", "rumus iup", "interp iup",
                "BPS", "Tahunan", "Lengkap", "Dinkes", "Tersedia", "Tahunan", 2025,
                None, None, None,
            ],
        ]
    )

    indikator, _metadata = baca_indikator_dan_metadata(wb)
    isv = next(i for i in indikator if i["id_indikator"] == "ISV-001")
    iup = next(i for i in indikator if i["id_indikator"] == "IUP-001")

    assert isv["arah_pembangunan"] == "Peningkatan Pendapatan per Kapita"
    assert isv["arah_ie"] is None
    assert iup["arah_ie"] == "IE1 - Kesehatan untuk Semua"
    assert iup["arah_pembangunan"] is None


def test_nomor_diturunkan_dari_suffix_id():
    wb = _wb_indikator(
        [
            [
                "ISV-087", "ISV", "Sasaran Visi", "Arah", "87", "Nama", "Tidak",
                None, None, None, None, None, None, None, None, None, None, None, None, None,
            ]
        ]
    )
    indikator, _metadata = baca_indikator_dan_metadata(wb)
    assert indikator[0]["nomor"] == 87
    assert indikator[0]["kode_indikator"] == "87"


def test_catatan_tiga_kolom_digabung_dengan_prefiks_dan_kolom_kosong_dilewati():
    wb = _wb_indikator(
        [
            [
                "ISV-001", "ISV", "Kelompok", "Arah", "1", "Nama", "Tidak",
                None, None, None, None, None, None, None, None, None, None,
                "Catatan A", None, "Catatan C",
            ]
        ]
    )
    indikator, _metadata = baca_indikator_dan_metadata(wb)
    assert indikator[0]["catatan_teknis"] == (
        "[Catatan Kualitas Data] Catatan A\n[Keterangan RPJMD / Catatan Kaltara] Catatan C"
    )


def test_metadata_ikut_terisi_dari_kolom_definisi_rumus_interpretasi():
    wb = _wb_indikator(
        [
            [
                "ISV-001", "ISV", "Kelompok", "Arah", "1", "Nama", "Tidak",
                "Definisi X", "Rumus X", "Interpretasi X", "Sumber X", "Tahunan",
                "Lengkap", "OPD X", "Tersedia", "Tahunan", 2025, None, None, None,
            ]
        ]
    )
    _indikator, metadata = baca_indikator_dan_metadata(wb)
    assert metadata[0] == {
        "id_indikator": "ISV-001",
        "definisi": "Definisi X",
        "rumus_mentah": "Rumus X",
        "interpretasi": "Interpretasi X",
        "sumber_data": "Sumber X",
        "frekuensi": "Tahunan",
        "status_metadata": "Lengkap",
    }


def test_baris_tanpa_id_indikator_dilewati():
    wb = _wb_indikator([[None] * 20])
    indikator, metadata = baca_indikator_dan_metadata(wb)
    assert indikator == []
    assert metadata == []


def _wb_nilai(baris: list[list]) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Data Target-Realisasi"
    ws.append(
        [
            "ID Indikator", "Kategori", "Kelompok / Pilar", "Kode Indikator",
            "Nama Indikator (Kaltara)", "Jenis Nilai", "Tahun", "Nilai (Angka)",
            "Nilai (Teks Asli)", "Satuan/Catatan",
        ]
    )
    for satu in baris:
        ws.append(satu)
    return wb


def test_baca_nilai_memetakan_jenis_dan_wilayah_provinsi():
    wb = _wb_nilai(
        [
            ["ISV-001", "ISV", "Kelompok", "1", "Nama", "Realisasi", 2021, 157.09, None, None],
            ["ISV-001", "ISV", "Kelompok", "1", "Nama", "Target", 2025, 227.1, None, None],
        ]
    )
    nilai = baca_nilai(wb)
    assert len(nilai) == 2
    assert nilai[0]["jenis"] == "realisasi"
    assert nilai[0]["wilayah_kode"] == "65"
    assert nilai[0]["periode"] is None
    assert nilai[0]["tahun"] == 2021
    assert nilai[0]["nilai"] == 157.09
    assert nilai[1]["jenis"] == "target"


def test_baca_nilai_melewati_baris_jenis_tidak_dikenal():
    wb = _wb_nilai([["ISV-001", "ISV", "Kelompok", "1", "Nama", "Bukan Jenis", 2021, 1.0, None, None]])
    assert baca_nilai(wb) == []


def test_baca_nilai_mempertahankan_teks_asli_dan_satuan_catatan():
    wb = _wb_nilai([["IUP-001", "IUP", "Kelompok", "1", "Nama", "Realisasi", 2020, None, "70,5", "angka sementara"]])
    nilai = baca_nilai(wb)
    assert nilai[0]["nilai"] is None
    assert nilai[0]["nilai_teks"] == "70,5"
    assert nilai[0]["satuan_catatan"] == "angka sementara"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/unit/test_ekspor_seed_indikator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.ekspor_seed_indikator'`.

- [ ] **Step 3: Write the export script**

Create `scripts/ekspor_seed_indikator.py`:

```python
"""Ekspor JSON fixture seed indikator dari Excel klasifikasi ISV/IUP.

Jalankan sekali secara manual setelah
`data/raw/BASIS_DATA_INDIKATOR_ISV-IUP_KALTARA.xlsx` tersedia. Hasilnya
(`backend/app/data/indikator_seed.json`) di-commit ke git; skrip ini sendiri
TIDAK dijalankan otomatis saat deploy — lihat `backend/app/cli.py`
(`seed-indikator`) untuk pemakaian fixture ini saat runtime.

Pemakaian:
    python scripts/ekspor_seed_indikator.py \
        data/raw/BASIS_DATA_INDIKATOR_ISV-IUP_KALTARA.xlsx \
        backend/app/data/indikator_seed.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

# Membuat `src` dapat diimpor ketika skrip dijalankan langsung sebagai
# `python scripts/ekspor_seed_indikator.py` (bukan lewat pytest, yang sudah
# menaruh akar repo di sys.path lewat konfigurasi `pythonpath` di pyproject.toml).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.etl.common import clean_text, parse_angka  # noqa: E402
from src.etl.transform.proxy import ekstrak_proxy  # noqa: E402

SHEET_INDIKATOR = "Basis Data Indikator"
SHEET_NILAI = "Data Target-Realisasi"
JUMLAH_INDIKATOR_DIHARAPKAN = 86

# Tiga kolom catatan mirip di sheet sumber, digabung jadi satu
# `indikator.catatan_teknis` supaya tidak ada informasi yang hilang.
KOLOM_CATATAN = (
    "Catatan Kualitas Data",
    "Keterangan (Rakor Kaltara)",
    "Keterangan RPJMD / Catatan Kaltara",
)


def _header(ws: Any) -> dict[str, int]:
    """Label header (baris 1) -> nomor kolom. Sama pola dengan indeks_header di src/etl/extract/master.py."""
    hasil: dict[str, int] = {}
    for kolom in range(1, ws.max_column + 1):
        label = clean_text(ws.cell(1, kolom).value)
        if label:
            hasil[label] = kolom
    return hasil


def baca_indikator_dan_metadata(wb: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Baris `indikator` + `metadata_indikator` dari sheet `Basis Data Indikator`."""
    ws = wb[SHEET_INDIKATOR]
    header = _header(ws)

    def sel(baris: int, label: str) -> Any:
        kolom = header.get(label)
        return ws.cell(baris, kolom).value if kolom else None

    indikator: list[dict[str, Any]] = []
    metadata: list[dict[str, Any]] = []

    for baris in range(2, ws.max_row + 1):
        id_indikator = clean_text(sel(baris, "ID Indikator"))
        if not id_indikator:
            continue

        kategori = (clean_text(sel(baris, "Kategori")) or "").upper()
        suffix = id_indikator.split("-")[-1]
        nomor = int(suffix) if suffix.isdigit() else None

        # "Arah Pembangunan" berarti dua hal berbeda tergantung kategori —
        # lihat catatan di docstring modul ini.
        kolom_arah = clean_text(sel(baris, "Arah Pembangunan"))
        arah_pembangunan = kolom_arah if kategori == "ISV" else None
        arah_ie = kolom_arah if kategori == "IUP" else None

        is_proxy, nama_proxy = ekstrak_proxy(
            sel(baris, "Indikator Proxy?"),
            sel(baris, "Keterangan RPJMD / Catatan Kaltara"),
        )

        catatan_gabungan = "\n".join(
            f"[{label}] {teks}"
            for label in KOLOM_CATATAN
            if (teks := clean_text(sel(baris, label)))
        )

        sumber_data = clean_text(sel(baris, "Sumber Data (RPJPD Provinsi)"))
        frekuensi = clean_text(sel(baris, "Frekuensi (RPJPD Provinsi)"))
        status_metadata = clean_text(sel(baris, "Status Metadata"))
        tahun_terakhir = parse_angka(sel(baris, "Tahun Data Terakhir"))

        indikator.append(
            {
                "id_indikator": id_indikator,
                "kategori": kategori,
                "nomor": nomor,
                "kode_indikator": clean_text(sel(baris, "Kode Indikator")),
                "nama_indikator": clean_text(sel(baris, "Nama Indikator (RPJPD Provinsi / dipakai Kaltara)")),
                "kelompok": clean_text(sel(baris, "Kelompok / Pilar")),
                "arah_pembangunan": arah_pembangunan,
                "arah_ie": arah_ie,
                "opd_pengampu": clean_text(sel(baris, "Perangkat Daerah Pengampu (Kaltara)")),
                "sumber_data": sumber_data,
                "frekuensi": frekuensi,
                "status_ketersediaan": clean_text(sel(baris, "Ketersediaan Data")),
                "status_metadata": status_metadata,
                "periode_data": clean_text(sel(baris, "Periode Data")),
                "tahun_terakhir": int(tahun_terakhir) if tahun_terakhir is not None else None,
                "is_proxy": bool(is_proxy),
                "nama_proxy": nama_proxy,
                "catatan_teknis": catatan_gabungan or None,
            }
        )
        metadata.append(
            {
                "id_indikator": id_indikator,
                "definisi": clean_text(sel(baris, "Definisi (RPJPD Provinsi)")),
                "rumus_mentah": clean_text(sel(baris, "Rumus Perhitungan (RPJPD Provinsi)")),
                "interpretasi": clean_text(sel(baris, "Interpretasi (RPJPD Provinsi)")),
                "sumber_data": sumber_data,
                "frekuensi": frekuensi,
                "status_metadata": status_metadata,
            }
        )

    return indikator, metadata


def baca_nilai(wb: Any) -> list[dict[str, Any]]:
    """Baris `nilai_indikator` (provinsi, tahunan) dari sheet `Data Target-Realisasi`."""
    ws = wb[SHEET_NILAI]
    header = _header(ws)

    def sel(baris: int, label: str) -> Any:
        kolom = header.get(label)
        return ws.cell(baris, kolom).value if kolom else None

    hasil: list[dict[str, Any]] = []
    for baris in range(2, ws.max_row + 1):
        id_indikator = clean_text(sel(baris, "ID Indikator"))
        if not id_indikator:
            continue

        jenis_teks = (clean_text(sel(baris, "Jenis Nilai")) or "").casefold()
        if jenis_teks == "realisasi":
            jenis = "realisasi"
        elif jenis_teks == "target":
            jenis = "target"
        else:
            continue

        tahun = parse_angka(sel(baris, "Tahun"))
        if tahun is None:
            continue

        hasil.append(
            {
                "id_indikator": id_indikator,
                "wilayah_kode": "65",
                "tahun": int(tahun),
                "jenis": jenis,
                "periode": None,
                "nilai": parse_angka(sel(baris, "Nilai (Angka)")),
                "nilai_teks": clean_text(sel(baris, "Nilai (Teks Asli)")),
                "satuan_catatan": clean_text(sel(baris, "Satuan/Catatan")),
                "sumber": "seed_awal:BASIS_DATA_INDIKATOR_ISV-IUP_KALTARA.xlsx",
            }
        )
    return hasil


def main(sumber: Path, target: Path) -> None:
    wb = load_workbook(sumber, data_only=True, read_only=True)
    indikator, metadata = baca_indikator_dan_metadata(wb)
    nilai = baca_nilai(wb)

    if len(indikator) != JUMLAH_INDIKATOR_DIHARAPKAN:
        raise SystemExit(
            f"Diharapkan {JUMLAH_INDIKATOR_DIHARAPKAN} baris indikator, didapat {len(indikator)}. "
            "Periksa apakah sheet 'Basis Data Indikator' berubah struktur."
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {"indikator": indikator, "metadata_indikator": metadata, "nilai_indikator": nilai},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Ditulis {len(indikator)} indikator, {len(nilai)} nilai -> {target}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
```

A note on `if (teks := clean_text(sel(baris, label)))` — this uses a walrus
assignment inside a generator expression's `if` clause, which is valid
Python 3.8+ syntax and keeps the "skip empty, keep label only when there's
content" logic in one line. If `ruff` flags anything here, prefer
readability: you may rewrite as an explicit loop instead, as long as the
behavior (skip blank/None cells, prefix each kept one with `[Label] `,
join with `\n`) stays identical to what the tests above expect.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/unit/test_ekspor_seed_indikator.py -v`
Expected: 9 passed.

- [ ] **Step 5: Lint, format, type-check**

Run: `ruff check scripts/ekspor_seed_indikator.py tests/unit/test_ekspor_seed_indikator.py`
Expected: clean. If it complains about the `noqa: E402` lines (imports not
at top of file), that's expected and already suppressed — those two imports
must come after the `sys.path.insert` line, which is why they're not at the
literal top of the file.

Run: `ruff format --check scripts/ekspor_seed_indikator.py tests/unit/test_ekspor_seed_indikator.py`

Run: `mypy scripts/ekspor_seed_indikator.py`
Expected: `Success: no issues found`. (`scripts/` may not be in mypy's normal
scan path — check `mypy.ini`/`pyproject.toml [tool.mypy]` `files`/`packages`
setting; if `scripts/` isn't covered, running `mypy scripts/ekspor_seed_indikator.py`
directly still type-checks that one file, which is enough here.)

- [ ] **Step 6: Commit**

```bash
git add scripts/ekspor_seed_indikator.py tests/unit/test_ekspor_seed_indikator.py
git commit -m "$(cat <<'EOF'
Tambah skrip ekspor JSON fixture seed indikator dari Excel klasifikasi

Baca sheet "Basis Data Indikator" + "Data Target-Realisasi", petakan ke
bentuk siap-insert tabel indikator/metadata_indikator/nilai_indikator.
Kolom "Arah Pembangunan" sengaja dipetakan beda per kategori (ISV ->
arah_pembangunan, IUP -> arah_ie) — lihat docstring modul.
EOF
)"
```

---

### Task 3: Generate and commit the actual seed fixture

**Files:**
- Create: `backend/app/data/indikator_seed.json` (generated, then committed)
- Test: `tests/integrasi/test_indikator_seed_json.py` (new)

**Interfaces:**
- Consumes: `scripts/ekspor_seed_indikator.py` from Task 2, and
  `data/raw/BASIS_DATA_INDIKATOR_ISV-IUP_KALTARA.xlsx` (must already exist
  locally — **if it does not exist, stop this task and tell the user**; do
  not fabricate a fixture).
- Produces: `backend/app/data/indikator_seed.json`, the exact file
  Task 4's CLI subcommand reads by default.

- [ ] **Step 1: Confirm the source file is present**

Run: `ls -la data/raw/BASIS_DATA_INDIKATOR_ISV-IUP_KALTARA.xlsx`

Expected: the file exists (any non-error `ls` output). If this command
errors with "No such file or directory", **stop here** and ask the user to
place the file before continuing this task.

- [ ] **Step 2: Generate the fixture**

Run:

```bash
mkdir -p backend/app/data
python scripts/ekspor_seed_indikator.py \
  data/raw/BASIS_DATA_INDIKATOR_ISV-IUP_KALTARA.xlsx \
  backend/app/data/indikator_seed.json
```

Expected output: `Ditulis 86 indikator, 660 nilai -> backend/app/data/indikator_seed.json`
(the nilai count may differ slightly from 660 if the source file has since
been edited — that's fine, this task doesn't hard-code that number anywhere
except the "86 indikator" guard already inside the script itself, which
already raised `SystemExit` in Step 2 if that count were wrong).

If the script exits with `SystemExit: Diharapkan 86 baris indikator, didapat N` —
stop and tell the user; the source file's row count doesn't match what
Task 2 assumed, and this needs a human decision (was a row added/removed on
purpose, or is the file wrong?), not a silent code change.

- [ ] **Step 3: Write the sanity test for the committed fixture**

Create `tests/integrasi/test_indikator_seed_json.py`:

```python
"""Tes kewarasan fixture backend/app/data/indikator_seed.json yang di-commit.

Ini bukan tes logic — filenya sudah statis. Tesnya menjaga fixture tidak
diam-diam rusak (duplikat PK, id_indikator salah format, dsb) di commit
berikutnya tanpa lewat scripts/ekspor_seed_indikator.py lagi.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

BERKAS = Path(__file__).resolve().parents[2] / "backend" / "app" / "data" / "indikator_seed.json"
POLA_ID = re.compile(r"^(ISV|IUP)-\d{3}$")


def _muatan() -> dict:
    return json.loads(BERKAS.read_text(encoding="utf-8"))


def test_berkas_ada():
    assert BERKAS.exists(), f"{BERKAS} belum digenerate — jalankan scripts/ekspor_seed_indikator.py"


def test_delapan_puluh_enam_indikator():
    muatan = _muatan()
    assert len(muatan["indikator"]) == 86


def test_setiap_id_indikator_format_tiga_digit():
    for baris in _muatan()["indikator"]:
        assert POLA_ID.match(baris["id_indikator"]), baris["id_indikator"]


def test_tidak_ada_id_indikator_duplikat():
    ids = [baris["id_indikator"] for baris in _muatan()["indikator"]]
    assert len(ids) == len(set(ids))


def test_setiap_indikator_punya_baris_metadata_pasangan():
    muatan = _muatan()
    ids_indikator = {baris["id_indikator"] for baris in muatan["indikator"]}
    ids_metadata = {baris["id_indikator"] for baris in muatan["metadata_indikator"]}
    assert ids_indikator == ids_metadata


def test_nilai_wilayah_selalu_provinsi_dan_jenis_valid():
    for baris in _muatan()["nilai_indikator"]:
        assert baris["wilayah_kode"] == "65"
        assert baris["jenis"] in ("realisasi", "target")


def test_nilai_id_indikator_semuanya_dikenal():
    muatan = _muatan()
    ids_indikator = {baris["id_indikator"] for baris in muatan["indikator"]}
    for baris in muatan["nilai_indikator"]:
        assert baris["id_indikator"] in ids_indikator


def test_tidak_ada_duplikat_kunci_nilai():
    kunci = [(b["id_indikator"], b["tahun"], b["jenis"]) for b in _muatan()["nilai_indikator"]]
    assert len(kunci) == len(set(kunci))
```

- [ ] **Step 4: Run the sanity tests**

Run: `python -m pytest tests/integrasi/test_indikator_seed_json.py -v`
Expected: 8 passed. If `test_delapan_puluh_enam_indikator` or any duplicate
check fails, go back to Task 2 — the mapping logic has a bug, don't patch
the JSON by hand.

- [ ] **Step 5: Commit**

```bash
git add backend/app/data/indikator_seed.json tests/integrasi/test_indikator_seed_json.py
git commit -m "$(cat <<'EOF'
Tambah fixture JSON seed 86 indikator + nilai baseline provinsi

Digenerate dari data/raw/BASIS_DATA_INDIKATOR_ISV-IUP_KALTARA.xlsx lewat
scripts/ekspor_seed_indikator.py. File Excel sumbernya tidak ikut commit
(data/raw/ tidak dilacak git); hasil generate ini yang jadi sumber
kebenaran untuk seed otomatis saat deploy (task berikutnya).
EOF
)"
```

---

### Task 4: CLI subcommand `seed-indikator`

**Files:**
- Modify: `backend/app/cli.py`
- Test: `tests/integrasi/test_cli.py` (add tests to existing file)

**Interfaces:**
- Consumes: `repo_indikator.jumlah()`, `repo_indikator.seed_massal()` (Task 1),
  `backend/app/data/indikator_seed.json` (Task 3), `backend.app.database.SessionLocal`
  (already exists, already imported in `cli.py`).
- Produces: `seed_indikator(session: Session, berkas: Path = BERKAS_SEED_INDIKATOR) -> int`
  (a pure, session-taking function — Task 5 does not need this, but tests
  do) and `perintah_seed_indikator() -> int` (the CLI entrypoint,
  `python -m backend.app.cli seed-indikator` calls this). Task 5
  (`docker-entrypoint.sh`) invokes the subcommand by name from the shell —
  it does not import any Python symbol directly.

**Context you need:** Open `backend/app/cli.py`. Note the existing split
between pure, session-taking, directly-testable functions
(`pastikan_wilayah(session)`, `seed_akun(session)` — neither commits, they
only `session.flush()`) and thin CLI wrappers that own their own
`SessionLocal()` and call `session.commit()` (`perintah_seed`,
`perintah_periksa`). You are adding one function of each kind, following
that exact split — this is required so the new logic can be tested against
the `session` pytest fixture (which is rolled back after each test, never
committed) instead of a real throwaway database.

For reference, here is the existing pattern you're mirroring (already in
the file, don't change it):

```python
def pastikan_wilayah(session: Session) -> int:
    """Isi wilayah yang belum ada. Idempoten."""
    dibuat = 0
    for kode, nama, tingkat, induk in WILAYAH_KALTARA:
        if session.get(Wilayah, kode) is None:
            session.add(Wilayah(kode=kode, nama=nama, tingkat=tingkat, parent_kode=induk, aktif=True))
            dibuat += 1
    session.flush()
    return dibuat
```

and its CLI wrapper:

```python
def perintah_seed(tampilkan_sandi: bool) -> int:
    with SessionLocal() as session:
        wilayah_baru = pastikan_wilayah(session)
        akun_baru = seed_akun(session)
        session.commit()
        print(f"Wilayah ditambahkan: {wilayah_baru}")
        ...
```

- [ ] **Step 1: Write the failing tests**

Add to the end of `tests/integrasi/test_cli.py` (keep the existing tests in
that file untouched, just append):

```python
def test_seed_indikator_mengisi_saat_kosong(session, tmp_path):
    import json

    from backend.app.cli import seed_indikator
    from backend.app.repositories import indikator as repo_indikator

    berkas = tmp_path / "seed.json"
    berkas.write_text(
        json.dumps(
            {
                "indikator": [
                    {"id_indikator": "ISV-001", "kategori": "ISV", "nomor": 1, "nama_indikator": "Contoh"}
                ],
                "metadata_indikator": [{"id_indikator": "ISV-001"}],
                "nilai_indikator": [
                    {
                        "id_indikator": "ISV-001",
                        "wilayah_kode": "65",
                        "tahun": 2021,
                        "jenis": "realisasi",
                        "nilai": 100.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    jumlah = seed_indikator(session, berkas)

    assert jumlah == 1
    assert repo_indikator.jumlah(session) == 1


def test_seed_indikator_dilewati_saat_sudah_terisi(session, tmp_path):
    import json

    from backend.app.cli import seed_indikator
    from backend.app.models import Indikator
    from backend.app.repositories import indikator as repo_indikator

    session.add(Indikator(id_indikator="ISV-001", kategori="ISV", nomor=1, nama_indikator="Sudah ada"))
    session.flush()

    berkas = tmp_path / "seed.json"
    berkas.write_text(
        json.dumps({"indikator": [], "metadata_indikator": [], "nilai_indikator": []}),
        encoding="utf-8",
    )

    jumlah = seed_indikator(session, berkas)

    assert jumlah == 0
    assert repo_indikator.jumlah(session) == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/integrasi/test_cli.py -k seed_indikator -v`
Expected: FAIL — `ImportError: cannot import name 'seed_indikator' from 'backend.app.cli'`.

- [ ] **Step 3: Implement the CLI subcommand**

Open `backend/app/cli.py`. Make three changes.

**3a.** Add imports. Find the existing import block near the top:

```python
from __future__ import annotations

import argparse
import secrets
import string
import sys

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import KODE_PROVINSI, Peran, Wilayah
from .repositories import pengguna as repo_pengguna
from .repositories import wilayah as repo_wilayah
from .security import hash_password
```

Change it to:

```python
from __future__ import annotations

import argparse
import json
import secrets
import string
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import KODE_PROVINSI, Peran, Wilayah
from .repositories import indikator as repo_indikator
from .repositories import pengguna as repo_pengguna
from .repositories import wilayah as repo_wilayah
from .security import hash_password
```

**3b.** Add a module-level constant and the two new functions. Insert this
right after the existing `OPERATOR_PER_WILAYAH = 2` line and before
`def sandi_acak(...)`:

```python
# Fixture di-generate scripts/ekspor_seed_indikator.py dari Excel klasifikasi
# ISV/IUP, di-commit ke git supaya deploy tidak butuh Excel sama sekali.
BERKAS_SEED_INDIKATOR = Path(__file__).resolve().parent / "data" / "indikator_seed.json"


def seed_indikator(session: Session, berkas: Path = BERKAS_SEED_INDIKATOR) -> int:
    """Isi indikator+metadata+nilai baseline dari fixture bila tabel kosong.

    Idempoten: mengembalikan 0 tanpa melakukan apa pun bila `indikator`
    sudah berisi baris apa pun — supaya redeploy tidak menduplikasi data.
    Tidak melakukan commit, sama seperti `pastikan_wilayah`/`seed_akun`.
    """
    if repo_indikator.jumlah(session) > 0:
        return 0

    muatan = json.loads(berkas.read_text(encoding="utf-8"))
    repo_indikator.seed_massal(
        session,
        indikator=muatan["indikator"],
        metadata=muatan["metadata_indikator"],
        nilai=muatan["nilai_indikator"],
    )
    session.flush()
    return len(muatan["indikator"])
```

**3c.** Add the CLI wrapper. Insert this right after the existing
`perintah_seed(...)` function (after its final `return 0` and blank line,
before `def perintah_periksa() -> int:`):

```python
def perintah_seed_indikator() -> int:
    with SessionLocal() as session:
        jumlah = seed_indikator(session)
        if jumlah == 0:
            print("Tabel indikator sudah terisi; seed dilewati.")
            return 0
        session.commit()
        print(f"Seed indikator selesai: {jumlah} indikator + nilai baseline ditambahkan.")
        return 0
```

**3d.** Wire the subcommand into argparse. Find this block near the bottom
of `main()`:

```python
    seed = sub.add_parser("seed", help="buat wilayah dan akun awal bila belum ada")
    seed.add_argument(
        "--tampilkan-sandi",
        action="store_true",
        help="cetak sandi awal ke layar (hanya di terminal yang aman)",
    )
    sub.add_parser("periksa", help="ringkasan kesiapan basis data")

    argumen = parser.parse_args(argv)
    if argumen.perintah == "seed":
        return perintah_seed(argumen.tampilkan_sandi)
    return perintah_periksa()
```

Change it to:

```python
    seed = sub.add_parser("seed", help="buat wilayah dan akun awal bila belum ada")
    seed.add_argument(
        "--tampilkan-sandi",
        action="store_true",
        help="cetak sandi awal ke layar (hanya di terminal yang aman)",
    )
    sub.add_parser("periksa", help="ringkasan kesiapan basis data")
    sub.add_parser(
        "seed-indikator",
        help="isi indikator+metadata+nilai baseline dari fixture bila tabel indikator kosong",
    )

    argumen = parser.parse_args(argv)
    if argumen.perintah == "seed":
        return perintah_seed(argumen.tampilkan_sandi)
    if argumen.perintah == "seed-indikator":
        return perintah_seed_indikator()
    return perintah_periksa()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/integrasi/test_cli.py -v`
Expected: all tests in the file pass, including the 2 new ones (the file
already had passing tests before this task — none of them should have
changed behavior).

- [ ] **Step 5: Manual CLI smoke test against a real throwaway database**

```bash
rm -f /tmp/sebatik-smoke.db
SEBATIK_DATABASE_URL="sqlite:////tmp/sebatik-smoke.db" \
  SEBATIK_SECRET_KEY="kunci-uji-yang-panjangnya-lebih-dari-32-karakter" \
  python -m alembic -c backend/alembic.ini upgrade head
SEBATIK_DATABASE_URL="sqlite:////tmp/sebatik-smoke.db" \
  SEBATIK_SECRET_KEY="kunci-uji-yang-panjangnya-lebih-dari-32-karakter" \
  python -m backend.app.cli seed-indikator
```

Expected on first run: `Seed indikator selesai: 86 indikator + nilai baseline ditambahkan.`

Run the exact same `seed-indikator` command a second time. Expected:
`Tabel indikator sudah terisi; seed dilewati.` — this proves the
"redeploy = no-op" requirement from the spec is actually satisfied, not just
theoretically idempotent.

Clean up: `rm -f /tmp/sebatik-smoke.db`

- [ ] **Step 6: Full backend regression (this is the step that proves Task 3's original test-collision bug is actually fixed)**

Run: `python -m pytest tests/api/ -v`
Expected: all tests pass, same count as before this plan started. If any
test in `tests/api/` now fails with an `IntegrityError` mentioning
`indikator` and a duplicate primary key — stop, this plan's core premise
(seeding via CLI, not Alembic migration, keeps `tests/api/conftest.py`'s
`_isi_benih()` collision-free) has been violated somewhere; do not patch
around it, re-read this plan's Global Constraints and find what diverged.

Run: `python -m pytest` (the whole suite)
Expected: all tests pass.

- [ ] **Step 7: Lint, format, type-check**

```bash
ruff check backend/app/cli.py tests/integrasi/test_cli.py
ruff format --check backend/app/cli.py tests/integrasi/test_cli.py
mypy backend/app/cli.py
```

Expected: all clean.

- [ ] **Step 8: Commit**

```bash
git add backend/app/cli.py tests/integrasi/test_cli.py
git commit -m "$(cat <<'EOF'
Tambah subcommand CLI seed-indikator, idempoten lewat cek COUNT

python -m backend.app.cli seed-indikator mengisi indikator+metadata+
nilai baseline dari backend/app/data/indikator_seed.json, tapi hanya
bila tabel indikator masih kosong. Sengaja bukan migrasi Alembic:
tests/api/conftest.py membangun skema tes lewat alembic upgrade head
lalu insert fixture Indikator dengan id yang sama dengan data produksi
(ISV-001, dst) — migrasi data akan menabraknya dengan IntegrityError.
EOF
)"
```

---

### Task 5: Wire the subcommand into `docker-entrypoint.sh`

**Files:**
- Modify: `docker-entrypoint.sh`

**Interfaces:**
- Consumes: `python -m backend.app.cli seed-indikator` (Task 4), invoked as
  a subprocess from the shell script — no Python-level interface.
- Produces: nothing further tasks depend on; this is the last task in this
  plan.

**Context you need:** Open `docker-entrypoint.sh` and find this block near
the end (the migration retry loop):

```sh
attempts=10
i=1
while [ "$i" -le "$attempts" ]; do
  echo "[entrypoint] alembic upgrade head (percobaan $i/$attempts)..."
  if python -m alembic -c backend/alembic.ini upgrade head; then
    echo "[entrypoint] skema mutakhir."
    break
  fi
  if [ "$i" -eq "$attempts" ]; then
    echo "[entrypoint] migrasi gagal setelah $attempts percobaan — berhenti." >&2
    exit 1
  fi
  i=$((i + 1))
  sleep 3
done

echo "[entrypoint] menjalankan server."
exec "$@"
```

- [ ] **Step 1: Add the seed call between migration success and server start**

Change the block above to:

```sh
attempts=10
i=1
while [ "$i" -le "$attempts" ]; do
  echo "[entrypoint] alembic upgrade head (percobaan $i/$attempts)..."
  if python -m alembic -c backend/alembic.ini upgrade head; then
    echo "[entrypoint] skema mutakhir."
    break
  fi
  if [ "$i" -eq "$attempts" ]; then
    echo "[entrypoint] migrasi gagal setelah $attempts percobaan — berhenti." >&2
    exit 1
  fi
  i=$((i + 1))
  sleep 3
done

# Seed indikator+metadata+nilai baseline sekali di deploy pertama; idempoten
# lewat cek COUNT di dalam perintahnya sendiri (lihat backend/app/cli.py),
# jadi aman dipanggil di setiap start container termasuk redeploy.
echo "[entrypoint] seed indikator (idempoten)..."
python -m backend.app.cli seed-indikator

echo "[entrypoint] menjalankan server."
exec "$@"
```

Do **not** wrap this new call in a retry loop like the migration above it —
by the time this line runs, the database is already confirmed reachable
(the migration right above it just succeeded), and the fixture file is
baked into the Docker image, so there is no "not ready yet" race to retry
for. The script already has `set -e` at the top, so if this command exits
non-zero for any other reason, the entrypoint stops and the deploy fails
loudly — which is the correct behavior (silent partial seeding would be
worse than a visible failed deploy).

- [ ] **Step 2: Verify shell syntax**

Run: `bash -n docker-entrypoint.sh`
Expected: no output (syntax is valid — this does not execute the script, only parses it).

- [ ] **Step 3: Manual end-to-end smoke test in a container-like environment**

If Docker is available locally, build and run the image to prove the full
chain works exactly as it will on Coolify:

```bash
docker build -t sebatik-smoke .
docker run --rm \
  -e SEBATIK_DATABASE_URL="sqlite:////app/data/processed/smoke.db" \
  -e SEBATIK_SECRET_KEY="kunci-uji-yang-panjangnya-lebih-dari-32-karakter" \
  sebatik-smoke sh -c \
  'python -m alembic -c backend/alembic.ini upgrade head && python -m backend.app.cli seed-indikator && python -m backend.app.cli periksa'
```

Expected: migration runs, then `Seed indikator selesai: 86 indikator + nilai
baseline ditambahkan.`, then the `periksa` summary prints without error.
This step is optional if Docker isn't available in your environment — the
Task 4 Step 5 smoke test already proves the same Python-level behavior
without a container; skip this step and note in your final report that it
was skipped and why, rather than silently omitting it.

- [ ] **Step 4: Commit**

```bash
git add docker-entrypoint.sh
git commit -m "$(cat <<'EOF'
Panggil seed-indikator di entrypoint setelah migrasi berhasil

Deploy pertama otomatis mengisi 86 indikator + nilai baseline provinsi
tanpa langkah manual; redeploy jadi no-op lewat cek COUNT di dalam
perintahnya sendiri (lihat backend/app/cli.py:seed_indikator).
EOF
)"
```

---

## Final check for this plan

After Task 5, run the complete verification sweep one more time from repo root:

```bash
python -m pytest --cov=backend/app --cov=src --cov-fail-under=80
ruff check .
ruff format --check .
mypy backend src
```

All four must be clean/passing. If coverage drops below 80%, the new files
in this plan (`scripts/ekspor_seed_indikator.py`, the `cli.py` additions)
are almost certainly the reason — the tests added in Tasks 2 and 4 already
exercise every branch described in this plan; if coverage still complains,
check for a branch you added that isn't described here (and therefore isn't
tested here) before adding tests just to satisfy the number.
