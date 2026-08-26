# Admin Manajemen Indikator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give admins a web page to fully manage the indicator catalog
(create, view, edit, delete `indikator` + its paired `metadata_indikator`
row) instead of needing a database console or a script.

**Architecture:** Five new endpoints under `/api/v1/admin/indikator*`
(list, detail, create, update, delete), admin-only, following this repo's
existing `router -> service -> repository -> model` layering exactly. The
update form is **full-replace**: the frontend always submits every editable
field, never a partial patch. A new React component,
`IndikatorManager.jsx`, renders the table and the create/edit form, mounted
as one more `Panel` inside the existing `AdminPage.jsx`.

**Tech Stack:** FastAPI 0.115+ (this plan uses `Annotated[Model, Form()]` —
a FastAPI feature available since 0.113, so the pinned `fastapi>=0.115,<1`
already supports it), SQLAlchemy 2.0, Pydantic v2, React 18 (no TypeScript,
no class components), Vitest for frontend tests, pytest for backend.

This plan assumes **Task A's plan** (`2026-08-27-seed-indikator.md`) is
already implemented and merged — specifically, it assumes 86 real
`indikator` rows already exist in any real deployment, and that
`tests/api/conftest.py`'s `_isi_benih()` fixture (5 hand-crafted test
indicators: `ISV-001`, `ISV-002`, `ISV-005`, `IUP-001`, `IUP-002`) is what
populates the test database. This plan's own tests use a **new** id,
`ISV-999`, specifically chosen to not collide with either set.

## Global Constraints

Re-read this section before each task.

- **Language convention:** Indonesian comments, commit messages, and
  identifiers in every backend file (matches every file you'll touch).
  Frontend JS/JSX identifiers in this repo are also Indonesian-flavored
  where the existing files already are (e.g. `SubmissionTable`,
  `AdminPage`), but component/prop names may stay in English where the
  existing component you're extending already does (e.g. `Panel`,
  `EmptyState` props) — match whatever the file you're editing already does,
  don't introduce a third convention.
- **Layering rule**, enforced by `tests/unit/test_arsitektur.py` (AST-based):
  - `backend/app/routers/admin.py` must never call
    `select()`/`insert()`/`update()`/`delete()`/`execute()` — only
    `backend/app/repositories/indikator.py` may build queries.
  - `backend/app/services/indikator.py` must never import `fastapi` or
    `starlette` — rejections are returned as `services.Penolakan(kode, pesan)`
    values, and the **router** translates them to `HTTPException`.
  - No router function may contain a `for`/`while` loop, and no router
    function may build a dict literal with more than 5 keys — both are
    checked by AST inspection. If you find yourself wanting either, that
    logic belongs in `services/indikator.py`, not the router.
  - `text("...")` (raw SQL) is banned outside `repositories/`.
- **Response shape convention (read before writing any endpoint):** every
  mutating endpoint in this app — `ubah_status_pengguna`, `reset_password`,
  `koreksi_arah_baik`, etc. — returns **200 OK with a small JSON body**
  (e.g. `{"status": "AKTIF"}`), never `201 Created` or `204 No Content`.
  This is not just a style preference: `frontend/src/api/client.js`'s
  `request()` function unconditionally calls `response.json()` on every
  successful response — a `204 No Content` response has no body, so
  `.json()` would throw in the browser. **Do not use 204 for the DELETE
  endpoint in this plan** even though generic REST guidance recommends it;
  return `{"status": "DIHAPUS"}` with 200, matching every other endpoint in
  this app.
- **Form parsing, not JSON bodies.** Every existing mutating endpoint in
  this app uses `Form(...)` scalar parameters (multipart/form-data), never
  a JSON request body — the frontend never calls `JSON.stringify` for a
  request, it always builds a `FormData`. This plan's create/update
  endpoints have ~30 editable fields each; instead of 30 separate `Form(...)`
  parameters (which the rest of this app uses for endpoints with 2-8
  fields), this plan uses `Annotated[SomePydanticModel, Form()]` — a single
  parameter whose fields FastAPI populates from the submitted form fields by
  name, one-to-one. The wire format the browser sends is unchanged
  (still `multipart/form-data`); only the Python-side function signature is
  grouped instead of flat. If you haven't used this FastAPI feature before:
  it requires `python-multipart` installed (already in
  `requirements.txt`) and works exactly like scalar `Form(...)` params
  except all fields live on one typed model instead of one signature
  parameter each.
- **Verification commands** (repo root):
  - `python -m pytest` — full backend suite.
  - `ruff check .` / `ruff format --check .` / `mypy backend src`
  - `cd frontend && pnpm lint && pnpm test && pnpm build`

---

### Task 1: Pydantic schemas for admin indikator CRUD

**Files:**
- Modify: `backend/app/schemas/indikator.py`

**Interfaces:**
- Consumes: nothing new (pure Pydantic, no DB access).
- Produces: `IndikatorFormDasar`, `IndikatorFormBuat(IndikatorFormDasar)`,
  `IndikatorAdminRingkas`, `DaftarIndikatorAdminResponse`,
  `MetadataIndikatorAdmin`, `IndikatorAdminDetailResponse`,
  `IndikatorDibuatResponse` — imported by name in Task 3 (service) and
  Task 4 (router).

This task has no automated test of its own — Pydantic model definitions
with no logic are exercised indirectly by every later task's tests. Skip
straight to writing the file; Task 3 and Task 4's tests will fail loudly if
any field name here is wrong.

- [ ] **Step 1: Add the schemas**

Open `backend/app/schemas/indikator.py`. It currently ends with
`ArahBaikResponse`. Append everything below to the end of the file:

```python
class IndikatorFormDasar(BaseModel):
    """Field yang bisa diisi/diedit admin lewat form CRUD.

    Dipakai dua kali: `IndikatorFormBuat` (create, + id_indikator) dan
    langsung sebagai body `PUT` (update, id_indikator datang dari path,
    bukan dari sini — lihat backend/app/routers/admin.py).

    `kategori`+`nomor` tetap wajib diisi bahkan saat update, supaya
    services.indikator.periksa_konsistensi_id bisa memvalidasi keduanya
    tetap cocok dengan id_indikator yang sudah ada (id_indikator sendiri
    tidak pernah bisa diubah setelah dibuat — itu primary key).
    """

    kategori: str
    nomor: int
    nama_indikator: str
    kode_indikator: str | None = None
    nama_asli: str | None = None
    kelompok: str | None = None
    arah_pembangunan: str | None = None
    sasaran_visi: str | None = None
    misi_agenda: str | None = None
    arah_ie: str | None = None
    indikator_induk: str | None = None
    kelompok_makro: str | None = None
    satuan: str | None = None
    penghasil: str | None = None
    kl_pengampu: str | None = None
    opd_pengampu: str | None = None
    tim_pjk: str | None = None
    sumber_data: str | None = None
    frekuensi: str | None = None
    status_ketersediaan: str | None = None
    status_metadata: str | None = None
    periode_data: str | None = None
    tahun_terakhir: int | None = None
    is_proxy: bool = False
    nama_proxy: str | None = None
    status_rpjmd: str | None = None
    kode_sdgs: str | None = None
    link_metadata: str | None = None
    link_publikasi: str | None = None
    link_data: str | None = None
    catatan_teknis: str | None = None
    # Field metadata_indikator yang tidak namanya sama dengan kolom indikator
    # di atas (definisi, sumber_data, frekuensi, status_metadata SUDAH ada
    # di atas dan ditulis ke dua tabel dengan nilai yang sama).
    definisi: str | None = None
    interpretasi: str | None = None
    rumus: str | None = None
    rumus_mentah: str | None = None
    rumus_latex: str | None = None
    halaman_sumber: str | None = None
    perlu_verifikasi_manual: bool = False
    sumber_metadata: str | None = None
    nama_di_buku1: str | None = None


class IndikatorFormBuat(IndikatorFormDasar):
    id_indikator: str


class IndikatorAdminRingkas(BaseModel):
    """Satu baris daftar admin — seluruh kolom `indikator`, tanpa metadata."""

    id_indikator: str
    kategori: str
    nomor: int | None = None
    kode_indikator: str | None = None
    nama_indikator: str
    nama_asli: str | None = None
    kelompok: str | None = None
    arah_pembangunan: str | None = None
    sasaran_visi: str | None = None
    misi_agenda: str | None = None
    arah_ie: str | None = None
    indikator_induk: str | None = None
    kelompok_makro: str | None = None
    satuan: str | None = None
    penghasil: str | None = None
    kl_pengampu: str | None = None
    opd_pengampu: str | None = None
    tim_pjk: str | None = None
    sumber_data: str | None = None
    frekuensi: str | None = None
    status_ketersediaan: str | None = None
    status_metadata: str | None = None
    periode_data: str | None = None
    tahun_terakhir: int | None = None
    is_proxy: bool
    nama_proxy: str | None = None
    status_rpjmd: str | None = None
    arah_baik: str | None = None
    arah_baik_terverifikasi: bool
    kode_sdgs: str | None = None
    link_metadata: str | None = None
    link_publikasi: str | None = None
    link_data: str | None = None
    catatan_teknis: str | None = None
    # Dihitung, bukan kolom asli — lihat services.indikator.daftar_admin.
    # Frontend menonaktifkan tombol hapus saat ini true.
    punya_nilai: bool


class DaftarIndikatorAdminResponse(BaseModel):
    data: list[IndikatorAdminRingkas]
    total: int
    page: int
    page_size: int


class MetadataIndikatorAdmin(BaseModel):
    definisi: str | None = None
    interpretasi: str | None = None
    sumber_data: str | None = None
    frekuensi: str | None = None
    rumus: str | None = None
    rumus_mentah: str | None = None
    rumus_latex: str | None = None
    halaman_sumber: str | None = None
    perlu_verifikasi_manual: bool = False
    sumber_metadata: str | None = None
    nama_di_buku1: str | None = None
    status_metadata: str | None = None


class IndikatorAdminDetailResponse(IndikatorAdminRingkas):
    metadata: MetadataIndikatorAdmin | None = None


class IndikatorDibuatResponse(BaseModel):
    status: str
    id_indikator: str
```

- [ ] **Step 2: Type-check and lint**

Run: `mypy backend/app/schemas/indikator.py`
Expected: `Success: no issues found`.

Run: `ruff check backend/app/schemas/indikator.py && ruff format --check backend/app/schemas/indikator.py`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/indikator.py
git commit -m "$(cat <<'EOF'
Tambah skema Pydantic untuk CRUD admin indikator

IndikatorFormDasar dipakai dua arah (create lewat IndikatorFormBuat,
update langsung) supaya field metadata_indikator dan indikator bisa
diisi dalam satu form, sesuai keputusan desain (lihat spec).
EOF
)"
```

---

### Task 2: Repository — count-with-values, create, update, delete

**Files:**
- Modify: `backend/app/repositories/indikator.py`
- Test: `tests/integrasi/test_repository_indikator_admin.py` (new)

**Interfaces:**
- Consumes: `Indikator`, `MetadataIndikator`, `NilaiIndikator` models; the
  `session` fixture from `tests/conftest.py`.
- Produces:
  `punya_nilai(session, id_indikator: str) -> bool`,
  `id_dengan_nilai(session, ids: Sequence[str]) -> set[str]`,
  `buat(session, indikator_fields: dict[str, object], metadata_fields: dict[str, object]) -> Indikator`,
  `perbarui(session, indikator: Indikator, metadata: MetadataIndikator | None, indikator_fields: dict[str, object], metadata_fields: dict[str, object]) -> dict[str, tuple[object, object]]`,
  `hapus(session, indikator: Indikator) -> None`.
  Task 3 (service layer) calls all five by exact name.

**Context: why `id_dengan_nilai` exists as a batch function, not a loop of
`punya_nilai` calls.** The admin list endpoint returns up to 200 rows per
page, each needing a "does this indicator have any recorded values?" flag
for the delete-button state. Calling `punya_nilai()` once per row would be
an N+1 query pattern — one query per row instead of one query for the whole
page. `id_dengan_nilai()` does it in a single `WHERE id_indikator IN (...)`
query; the service (Task 3) calls it once with all the page's ids, then
checks set membership per row in Python. This mirrors the "N+1 Query
Prevention — batch fetch" pattern: fetch once, build a lookup structure,
then do a cheap per-row lookup instead of a per-row query.

**Context: why `perbarui()` returns a diff dict.** The spec requires a
`LogPerubahan` audit row **per field that actually changed**, not one row
per field submitted (most submitted fields won't have changed — full-replace
semantics still resubmits unchanged fields every time). Computing "what
changed" requires comparing old vs. new values before overwriting them,
which only the repository function can do cleanly since it's the one
holding both the ORM object (old values) and the incoming dict (new
values) at the same moment.

- [ ] **Step 1: Write the failing tests**

Create `tests/integrasi/test_repository_indikator_admin.py`:

```python
"""Tes repository.indikator: cek nilai massal, buat, perbarui, hapus."""

from __future__ import annotations

from backend.app.repositories import indikator as repo_indikator


def _indikator_dasar(session, id_indikator="ISV-999", **ubah):
    from backend.app.models import Indikator

    baku = {"id_indikator": id_indikator, "kategori": "ISV", "nomor": 999, "nama_indikator": "Uji"}
    obj = Indikator(**{**baku, **ubah})
    session.add(obj)
    session.flush()
    return obj


def test_punya_nilai_false_saat_tidak_ada_nilai(session):
    _indikator_dasar(session)
    assert repo_indikator.punya_nilai(session, "ISV-999") is False


def test_punya_nilai_true_saat_ada_nilai(session):
    from backend.app.models import NilaiIndikator

    _indikator_dasar(session)
    session.add(NilaiIndikator(id_indikator="ISV-999", wilayah_kode="65", tahun=2021, jenis="realisasi", nilai=1.0))
    session.flush()
    assert repo_indikator.punya_nilai(session, "ISV-999") is True


def test_id_dengan_nilai_hanya_mengembalikan_yang_punya_nilai(session):
    from backend.app.models import NilaiIndikator

    _indikator_dasar(session, "ISV-999")
    _indikator_dasar(session, "ISV-998", nomor=998)
    session.add(NilaiIndikator(id_indikator="ISV-999", wilayah_kode="65", tahun=2021, jenis="realisasi", nilai=1.0))
    session.flush()

    assert repo_indikator.id_dengan_nilai(session, ["ISV-999", "ISV-998"]) == {"ISV-999"}


def test_id_dengan_nilai_kosong_untuk_daftar_kosong(session):
    assert repo_indikator.id_dengan_nilai(session, []) == set()


def test_buat_insert_indikator_dan_metadata(session):
    from backend.app.models import Indikator, MetadataIndikator

    indikator = repo_indikator.buat(
        session,
        indikator_fields={"id_indikator": "ISV-999", "kategori": "ISV", "nomor": 999, "nama_indikator": "Baru"},
        metadata_fields={"definisi": "Definisi baru"},
    )
    session.flush()

    assert indikator.id_indikator == "ISV-999"
    assert session.get(Indikator, "ISV-999").nama_indikator == "Baru"
    assert session.get(MetadataIndikator, "ISV-999").definisi == "Definisi baru"


def test_perbarui_hanya_mencatat_field_yang_benar_benar_berubah(session):
    from backend.app.models import MetadataIndikator

    indikator = _indikator_dasar(session, nama_indikator="Lama", kelompok="Kelompok Lama")
    metadata = MetadataIndikator(id_indikator="ISV-999", definisi="Definisi lama")
    session.add(metadata)
    session.flush()

    perubahan = repo_indikator.perbarui(
        session,
        indikator,
        metadata,
        indikator_fields={"kategori": "ISV", "nomor": 999, "nama_indikator": "Lama", "kelompok": "Kelompok Baru"},
        metadata_fields={"definisi": "Definisi lama"},
    )

    assert perubahan == {"kelompok": ("Kelompok Lama", "Kelompok Baru")}
    assert indikator.nama_indikator == "Lama"
    assert indikator.kelompok == "Kelompok Baru"


def test_perbarui_membuat_baris_metadata_bila_belum_ada(session):
    from backend.app.models import MetadataIndikator

    indikator = _indikator_dasar(session)

    repo_indikator.perbarui(
        session,
        indikator,
        None,
        indikator_fields={"kategori": "ISV", "nomor": 999, "nama_indikator": "Uji"},
        metadata_fields={"definisi": "Definisi baru"},
    )
    session.flush()

    assert session.get(MetadataIndikator, "ISV-999").definisi == "Definisi baru"


def test_hapus_menghapus_indikator(session):
    from backend.app.models import Indikator

    indikator = _indikator_dasar(session)
    repo_indikator.hapus(session, indikator)
    session.flush()

    assert session.get(Indikator, "ISV-999") is None


def test_hapus_ikut_menghapus_metadata_lewat_cascade(session):
    from backend.app.models import Indikator, MetadataIndikator

    indikator = _indikator_dasar(session)
    session.add(MetadataIndikator(id_indikator="ISV-999"))
    session.flush()

    repo_indikator.hapus(session, indikator)
    session.flush()

    assert session.get(Indikator, "ISV-999") is None
    assert session.get(MetadataIndikator, "ISV-999") is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/integrasi/test_repository_indikator_admin.py -v`
Expected: FAIL — `AttributeError: module 'backend.app.repositories.indikator' has no attribute 'punya_nilai'` (and similar for the other four).

- [ ] **Step 3: Implement the five repository functions**

Open `backend/app/repositories/indikator.py`. You should already have, from
the seed-indikator plan, `insert` imported and `NilaiIndikator` imported —
if this plan is being implemented independently (Task A not done yet),
change the import block at the top from:

```python
from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.orm import Session

from ..models import Indikator, MetadataIndikator, StatusVerifikasi
```

to:

```python
from collections.abc import Sequence

from sqlalchemy import Select, asc, desc, func, select
from sqlalchemy.orm import Session

from ..models import Indikator, MetadataIndikator, NilaiIndikator, StatusVerifikasi
```

(If `NilaiIndikator` and `Sequence` are already imported because Task A ran
first, just add whichever of the two is missing — don't duplicate an
existing import.)

Then add these five functions at the end of the file (after
`ubah_arah_baik`):

```python
def punya_nilai(session: Session, id_indikator: str) -> bool:
    stmt = select(NilaiIndikator.id).where(NilaiIndikator.id_indikator == id_indikator).limit(1)
    return session.scalars(stmt).first() is not None


def id_dengan_nilai(session: Session, ids: Sequence[str]) -> set[str]:
    """Subset dari `ids` yang punya minimal satu baris `nilai_indikator`.

    Satu query untuk seluruh halaman, bukan satu query per baris — lihat
    catatan N+1 di plan yang menambah fungsi ini.
    """
    if not ids:
        return set()
    stmt = select(NilaiIndikator.id_indikator.distinct()).where(NilaiIndikator.id_indikator.in_(ids))
    return set(session.scalars(stmt))


def buat(
    session: Session,
    indikator_fields: dict[str, object],
    metadata_fields: dict[str, object],
) -> Indikator:
    """Buat indikator+metadata baru. Tidak commit — pemanggil (service) yang commit."""
    indikator = Indikator(**indikator_fields)
    session.add(indikator)
    session.flush()  # perlu id_indikator terisi sebelum baris metadata dibuat
    session.add(MetadataIndikator(id_indikator=indikator.id_indikator, **metadata_fields))
    return indikator


def perbarui(
    session: Session,
    indikator: Indikator,
    metadata: MetadataIndikator | None,
    indikator_fields: dict[str, object],
    metadata_fields: dict[str, object],
) -> dict[str, tuple[object, object]]:
    """Terapkan field baru; kembalikan {field: (lama, baru)} hanya utk field yang berubah.

    Dipakai pemanggil (service) untuk menulis satu baris LogPerubahan per
    field yang benar-benar berubah nilainya.
    """
    perubahan: dict[str, tuple[object, object]] = {}

    for field, baru in indikator_fields.items():
        lama = getattr(indikator, field)
        if lama != baru:
            perubahan[field] = (lama, baru)
            setattr(indikator, field, baru)

    if metadata is None:
        metadata = MetadataIndikator(id_indikator=indikator.id_indikator)
        session.add(metadata)
    for field, baru in metadata_fields.items():
        lama = getattr(metadata, field)
        if lama != baru:
            perubahan[f"metadata.{field}"] = (lama, baru)
            setattr(metadata, field, baru)

    return perubahan


def hapus(session: Session, indikator: Indikator) -> None:
    """Hapus indikator. `metadata_indikator` dan `nilai_indikator` ikut terhapus

    lewat FK `ondelete="CASCADE"` yang sudah ada di skema (lihat
    backend/app/models/indikator.py) — tidak perlu dihapus manual di sini.
    Pemanggil (service) yang memastikan lewat `punya_nilai()` bahwa memang
    boleh dihapus SEBELUM memanggil fungsi ini.
    """
    session.delete(indikator)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/integrasi/test_repository_indikator_admin.py -v`
Expected: 9 passed.

- [ ] **Step 5: Lint, format, type-check**

```bash
ruff check backend/app/repositories/indikator.py tests/integrasi/test_repository_indikator_admin.py
ruff format --check backend/app/repositories/indikator.py tests/integrasi/test_repository_indikator_admin.py
mypy backend/app/repositories/indikator.py
```

Expected: all clean.

- [ ] **Step 6: Commit**

```bash
git add backend/app/repositories/indikator.py tests/integrasi/test_repository_indikator_admin.py
git commit -m "$(cat <<'EOF'
Tambah repository CRUD indikator: buat/perbarui/hapus/cek nilai

perbarui() mengembalikan diff field yang benar-benar berubah, dipakai
audit LogPerubahan di service layer. id_dengan_nilai() satu query utk
satu halaman daftar, menghindari N+1 per baris.
EOF
)"
```

---

### Task 3: Service layer — validation, field split, orchestration

**Files:**
- Modify: `backend/app/services/indikator.py`
- Test: `tests/integrasi/test_service_indikator_admin.py` (new)

**Interfaces:**
- Consumes: `repo_indikator.{punya_nilai,id_dengan_nilai,buat,perbarui,hapus}`
  (Task 2), `repo_tata_kelola.{catat_perubahan,catat_aktivitas}` (already
  exist — see `backend/app/repositories/tata_kelola.py`), `services.Penolakan`
  (already exists in `backend/app/services/__init__.py`), the Pydantic
  models from Task 1.
- Produces: `periksa_konsistensi_id(id_indikator, kategori, nomor) -> Penolakan | None`,
  `periksa_penghapusan(session, id_indikator) -> Penolakan | None`,
  `buat_indikator(session, form, *, pengguna_id) -> Indikator`,
  `perbarui_indikator(session, indikator, metadata, form, *, pengguna_id) -> dict`,
  `hapus_indikator(session, indikator, *, pengguna_id) -> dict`,
  `daftar_admin(session, **kwargs) -> dict`, `detail_admin(session, indikator) -> dict`.
  Task 4 (router) calls every one of these by exact name.

**Context: why `kategori`/`nomor` are still validated on update even though
the plan's frontend will render them read-only.** `id_indikator` is the
primary key and is never updated once a row exists. If an update request's
`kategori`/`nomor` don't match what the existing `id_indikator` implies
(e.g. someone edits the form's hidden fields, or a future UI bug sends the
wrong value), silently accepting it would leave `indikator.kategori` /
`indikator.nomor` inconsistent with `indikator.id_indikator` forever — with
no way to fix it except manual SQL, since there's no "rename" endpoint.
Rejecting the mismatch with 422 keeps that invariant enforced at the only
place that can still catch it.

**Context: why `is_proxy`/`perlu_verifikasi_manual` don't need special
handling for "unchecked checkbox."** An HTML checkbox that is **unchecked**
is omitted entirely from the submitted form data (this is native browser
behavior, not something this codebase controls). Because
`IndikatorFormDasar.is_proxy` and `.perlu_verifikasi_manual` both have
`= False` as their Pydantic default, FastAPI's `Form()`-with-model
validates a submission that's missing that key using the model default —
which is exactly what "checkbox was left unchecked" should mean. You do not
need to add any `if "is_proxy" not in form_data` logic anywhere; this is
handled by Pydantic defaults automatically. This is called out here because
it's easy to assume you need extra handling and add dead code for it.

- [ ] **Step 1: Write the failing tests**

Create `tests/integrasi/test_service_indikator_admin.py`:

```python
"""Tes service.indikator: validasi CRUD admin dan orkestrasi audit."""

from __future__ import annotations

import pytest

from backend.app.schemas.indikator import IndikatorFormBuat, IndikatorFormDasar
from backend.app.services import indikator as svc


def _form_buat(**ubah) -> IndikatorFormBuat:
    baku = {"id_indikator": "ISV-999", "kategori": "ISV", "nomor": 999, "nama_indikator": "Uji"}
    return IndikatorFormBuat(**{**baku, **ubah})


def _form_dasar(**ubah) -> IndikatorFormDasar:
    baku = {"kategori": "ISV", "nomor": 999, "nama_indikator": "Uji"}
    return IndikatorFormDasar(**{**baku, **ubah})


@pytest.mark.parametrize(
    "id_indikator,kategori,nomor,valid",
    [
        ("ISV-999", "ISV", 999, True),
        ("ISV-001", "ISV", 999, False),  # nomor tidak cocok id
        ("ISV-999", "IUP", 999, False),  # kategori tidak cocok prefiks id
        ("XYZ-001", "XYZ", 1, False),  # kategori bukan ISV/IUP
    ],
)
def test_periksa_konsistensi_id(id_indikator, kategori, nomor, valid):
    penolakan = svc.periksa_konsistensi_id(id_indikator, kategori, nomor)
    assert (penolakan is None) is valid
    if penolakan:
        assert penolakan.kode == 422


def test_periksa_penghapusan_diizinkan_tanpa_nilai(session):
    from backend.app.models import Indikator

    session.add(Indikator(id_indikator="ISV-999", kategori="ISV", nomor=999, nama_indikator="Uji"))
    session.flush()
    assert svc.periksa_penghapusan(session, "ISV-999") is None


def test_periksa_penghapusan_diblokir_saat_ada_nilai(session):
    from backend.app.models import Indikator, NilaiIndikator

    session.add(Indikator(id_indikator="ISV-999", kategori="ISV", nomor=999, nama_indikator="Uji"))
    session.add(NilaiIndikator(id_indikator="ISV-999", wilayah_kode="65", tahun=2021, jenis="realisasi", nilai=1.0))
    session.flush()

    penolakan = svc.periksa_penghapusan(session, "ISV-999")
    assert penolakan is not None
    assert penolakan.kode == 409


def test_buat_indikator_insert_dan_mencatat_aktivitas(session):
    from backend.app.models import Indikator, LogAktivitas

    indikator = svc.buat_indikator(session, _form_buat(), pengguna_id=1)

    assert isinstance(indikator, Indikator)
    log = session.query(LogAktivitas).filter_by(objek_id="ISV-999").one()
    assert log.aksi == "indikator_dibuat"


def test_buat_indikator_menyalin_field_kembar_ke_metadata(session):
    from backend.app.models import MetadataIndikator

    svc.buat_indikator(session, _form_buat(sumber_data="BPS", definisi="Definisi X"), pengguna_id=1)

    metadata = session.get(MetadataIndikator, "ISV-999")
    assert metadata.sumber_data == "BPS"
    assert metadata.definisi == "Definisi X"


def test_perbarui_indikator_mencatat_log_perubahan_hanya_untuk_field_berubah(session):
    from backend.app.models import LogPerubahan
    from backend.app.repositories import indikator as repo_indikator

    indikator = svc.buat_indikator(session, _form_buat(kelompok="Lama"), pengguna_id=1)
    session.flush()
    metadata = repo_indikator.ambil_metadata(session, "ISV-999")

    hasil = svc.perbarui_indikator(session, indikator, metadata, _form_dasar(kelompok="Baru"), pengguna_id=2)

    assert hasil["status"] == "DIPERBARUI"
    log = session.query(LogPerubahan).filter_by(id_indikator="ISV-999", field="kelompok").one()
    assert log.nilai_lama == "Lama"
    assert log.nilai_baru == "Baru"
    assert log.pengguna_id == 2


def test_hapus_indikator_mencatat_aktivitas_dan_menghapus_baris(session):
    from backend.app.models import Indikator, LogAktivitas

    indikator = svc.buat_indikator(session, _form_buat(), pengguna_id=1)
    session.flush()

    hasil = svc.hapus_indikator(session, indikator, pengguna_id=2)

    assert hasil == {"status": "DIHAPUS"}
    assert session.get(Indikator, "ISV-999") is None
    log = session.query(LogAktivitas).filter_by(objek_id="ISV-999", aksi="indikator_dihapus").one()
    assert log.pengguna_id == 2


def test_daftar_admin_menandai_punya_nilai_dengan_benar(session):
    from backend.app.models import NilaiIndikator

    svc.buat_indikator(session, _form_buat(), pengguna_id=1)
    svc.buat_indikator(session, _form_buat(id_indikator="ISV-998", nomor=998), pengguna_id=1)
    session.add(NilaiIndikator(id_indikator="ISV-999", wilayah_kode="65", tahun=2021, jenis="realisasi", nilai=1.0))
    session.commit()

    hasil = svc.daftar_admin(
        session, q=None, kategori=None, kelompok=None, tim=None, sort="id_indikator", order="asc", page=1, page_size=200
    )
    per_id = {baris["id_indikator"]: baris for baris in hasil["data"]}
    assert per_id["ISV-999"]["punya_nilai"] is True
    assert per_id["ISV-998"]["punya_nilai"] is False


def test_detail_admin_menyertakan_metadata(session):
    indikator = svc.buat_indikator(session, _form_buat(definisi="Definisi Y"), pengguna_id=1)
    session.commit()

    hasil = svc.detail_admin(session, indikator)
    assert hasil["metadata"]["definisi"] == "Definisi Y"
    assert hasil["punya_nilai"] is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/integrasi/test_service_indikator_admin.py -v`
Expected: FAIL — `AttributeError: module 'backend.app.services.indikator' has no attribute 'periksa_konsistensi_id'` (and similarly for the rest).

- [ ] **Step 3: Implement the service functions**

Open `backend/app/services/indikator.py`. Change the import block at the
top from:

```python
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..models import KODE_PROVINSI, ArahBaik, Indikator
from ..repositories import indikator as repo_indikator
from ..repositories import nilai as repo_nilai
from ..repositories import tata_kelola as repo_tata_kelola
from . import capaian as svc_capaian
```

to:

```python
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..models import KODE_PROVINSI, ArahBaik, Indikator, MetadataIndikator
from ..repositories import indikator as repo_indikator
from ..repositories import nilai as repo_nilai
from ..repositories import tata_kelola as repo_tata_kelola
from ..schemas.indikator import IndikatorFormBuat, IndikatorFormDasar
from . import Penolakan
from . import capaian as svc_capaian
```

Then append everything below to the end of the file (after
`ubah_arah_baik`, the last function currently in the file):

```python
# --- CRUD admin -------------------------------------------------------------
#
# Field indikator yang boleh diisi/diedit lewat form admin. `arah_baik` dan
# `arah_baik_terverifikasi` sengaja TIDAK di sini — itu tetap lewat
# koreksi_arah_baik()/endpoint /arah-baik/{id} yang sudah ada, supaya tidak
# ada dua jalur yang menulis field yang sama. `status_verifikasi` juga tidak
# di sini — selalu DISETUJUI untuk data yang ditulis admin.
FIELD_INDIKATOR_EDITABLE = (
    "kategori",
    "nomor",
    "kode_indikator",
    "nama_indikator",
    "nama_asli",
    "kelompok",
    "arah_pembangunan",
    "sasaran_visi",
    "misi_agenda",
    "arah_ie",
    "indikator_induk",
    "kelompok_makro",
    "satuan",
    "penghasil",
    "kl_pengampu",
    "opd_pengampu",
    "tim_pjk",
    "sumber_data",
    "frekuensi",
    "status_ketersediaan",
    "status_metadata",
    "periode_data",
    "tahun_terakhir",
    "is_proxy",
    "nama_proxy",
    "status_rpjmd",
    "kode_sdgs",
    "link_metadata",
    "link_publikasi",
    "link_data",
    "catatan_teknis",
)
# Field metadata_indikator yang boleh diedit. sumber_data/frekuensi/
# status_metadata sengaja SAMA NAMA dengan tiga field indikator di atas —
# _pisahkan_field() menyalin nilai form yang sama ke dua tabel itu.
FIELD_METADATA_EDITABLE = (
    "definisi",
    "interpretasi",
    "sumber_data",
    "frekuensi",
    "rumus",
    "rumus_mentah",
    "rumus_latex",
    "halaman_sumber",
    "perlu_verifikasi_manual",
    "sumber_metadata",
    "nama_di_buku1",
    "status_metadata",
)


def _kosong_jadi_none(nilai: Any) -> Any:
    """String kosong dari form berarti "kosongkan field ini", bukan literal string kosong."""
    if isinstance(nilai, str) and nilai.strip() == "":
        return None
    return nilai


def _pisahkan_field(form: IndikatorFormDasar) -> tuple[dict[str, Any], dict[str, Any]]:
    """Form gabungan -> (field utk tabel indikator, field utk metadata_indikator)."""
    muatan = form.model_dump()
    indikator_fields = {f: _kosong_jadi_none(muatan[f]) for f in FIELD_INDIKATOR_EDITABLE}
    metadata_fields = {f: _kosong_jadi_none(muatan[f]) for f in FIELD_METADATA_EDITABLE}
    return indikator_fields, metadata_fields


def periksa_konsistensi_id(id_indikator: str, kategori: str, nomor: int) -> Penolakan | None:
    """`id_indikator` harus selalu `f"{kategori}-{nomor:03d}"` — dicek di create DAN update.

    Dipanggil dengan id_indikator dari form saat create, dan dari path saat
    update (lihat backend/app/routers/admin.py) — supaya submit yang
    mencoba mengubah kategori/nomor jadi tidak konsisten dengan
    id_indikator yang sudah ada (primary key, tidak pernah berubah) ditolak.
    """
    if kategori not in ("ISV", "IUP"):
        return Penolakan(422, "Kategori harus ISV atau IUP")
    diharapkan = f"{kategori}-{nomor:03d}"
    if id_indikator != diharapkan:
        return Penolakan(
            422,
            f"id_indikator harus konsisten dengan kategori+nomor "
            f"(diharapkan '{diharapkan}', dapat '{id_indikator}')",
        )
    return None


def periksa_penghapusan(session: Session, id_indikator: str) -> Penolakan | None:
    if repo_indikator.punya_nilai(session, id_indikator):
        return Penolakan(409, "Indikator masih punya histori nilai; tidak dapat dihapus")
    return None


def buat_indikator(session: Session, form: IndikatorFormBuat, *, pengguna_id: int | None) -> Indikator:
    indikator_fields, metadata_fields = _pisahkan_field(form)
    indikator_fields["id_indikator"] = form.id_indikator
    indikator = repo_indikator.buat(session, indikator_fields, metadata_fields)
    repo_tata_kelola.catat_aktivitas(
        session,
        pengguna_id=pengguna_id,
        aksi="indikator_dibuat",
        objek_tipe="indikator",
        objek_id=indikator.id_indikator,
        detail=None,
    )
    session.commit()
    return indikator


def perbarui_indikator(
    session: Session,
    indikator: Indikator,
    metadata: MetadataIndikator | None,
    form: IndikatorFormDasar,
    *,
    pengguna_id: int | None,
) -> dict[str, Any]:
    indikator_fields, metadata_fields = _pisahkan_field(form)
    perubahan = repo_indikator.perbarui(session, indikator, metadata, indikator_fields, metadata_fields)
    for field, (lama, baru) in perubahan.items():
        repo_tata_kelola.catat_perubahan(
            session,
            pengguna_id=pengguna_id,
            id_indikator=indikator.id_indikator,
            field=field,
            nilai_lama=str(lama) if lama is not None else None,
            nilai_baru=str(baru) if baru is not None else None,
            sumber_perubahan="edit_admin",
        )
    session.commit()
    return {"status": "DIPERBARUI"}


def hapus_indikator(session: Session, indikator: Indikator, *, pengguna_id: int | None) -> dict[str, str]:
    id_indikator = indikator.id_indikator
    repo_tata_kelola.catat_aktivitas(
        session,
        pengguna_id=pengguna_id,
        aksi="indikator_dihapus",
        objek_tipe="indikator",
        objek_id=id_indikator,
        detail={"nama_indikator": indikator.nama_indikator, "kategori": indikator.kategori},
    )
    repo_indikator.hapus(session, indikator)
    session.commit()
    return {"status": "DIHAPUS"}


def _ringkas_admin(indikator: Indikator, punya_nilai: bool) -> dict[str, Any]:
    return {
        "id_indikator": indikator.id_indikator,
        "kategori": indikator.kategori,
        "nomor": indikator.nomor,
        "kode_indikator": indikator.kode_indikator,
        "nama_indikator": indikator.nama_indikator,
        "nama_asli": indikator.nama_asli,
        "kelompok": indikator.kelompok,
        "arah_pembangunan": indikator.arah_pembangunan,
        "sasaran_visi": indikator.sasaran_visi,
        "misi_agenda": indikator.misi_agenda,
        "arah_ie": indikator.arah_ie,
        "indikator_induk": indikator.indikator_induk,
        "kelompok_makro": indikator.kelompok_makro,
        "satuan": indikator.satuan,
        "penghasil": indikator.penghasil,
        "kl_pengampu": indikator.kl_pengampu,
        "opd_pengampu": indikator.opd_pengampu,
        "tim_pjk": indikator.tim_pjk,
        "sumber_data": indikator.sumber_data,
        "frekuensi": indikator.frekuensi,
        "status_ketersediaan": indikator.status_ketersediaan,
        "status_metadata": indikator.status_metadata,
        "periode_data": indikator.periode_data,
        "tahun_terakhir": indikator.tahun_terakhir,
        "is_proxy": indikator.is_proxy,
        "nama_proxy": indikator.nama_proxy,
        "status_rpjmd": indikator.status_rpjmd,
        "arah_baik": indikator.arah_baik,
        "arah_baik_terverifikasi": indikator.arah_baik_terverifikasi,
        "kode_sdgs": indikator.kode_sdgs,
        "link_metadata": indikator.link_metadata,
        "link_publikasi": indikator.link_publikasi,
        "link_data": indikator.link_data,
        "catatan_teknis": indikator.catatan_teknis,
        "punya_nilai": punya_nilai,
    }


def daftar_admin(
    session: Session,
    *,
    q: str | None,
    kategori: list[str] | None,
    kelompok: list[str] | None,
    tim: list[str] | None,
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Daftar admin berhalaman — semua kolom indikator, bukan hanya FIELD_PUBLIK."""
    daftar, total = repo_indikator.cari(
        session,
        q=q,
        kategori=kategori,
        kelompok=kelompok,
        tim=tim,
        status_metadata=None,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )
    dengan_nilai = repo_indikator.id_dengan_nilai(session, [item.id_indikator for item in daftar])
    return {
        "data": [_ringkas_admin(item, item.id_indikator in dengan_nilai) for item in daftar],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def detail_admin(session: Session, indikator: Indikator) -> dict[str, Any]:
    metadata = repo_indikator.ambil_metadata(session, indikator.id_indikator)
    hasil = _ringkas_admin(indikator, repo_indikator.punya_nilai(session, indikator.id_indikator))
    hasil["metadata"] = (
        None
        if metadata is None
        else {
            "definisi": metadata.definisi,
            "interpretasi": metadata.interpretasi,
            "sumber_data": metadata.sumber_data,
            "frekuensi": metadata.frekuensi,
            "rumus": metadata.rumus,
            "rumus_mentah": metadata.rumus_mentah,
            "rumus_latex": metadata.rumus_latex,
            "halaman_sumber": metadata.halaman_sumber,
            "perlu_verifikasi_manual": metadata.perlu_verifikasi_manual,
            "sumber_metadata": metadata.sumber_metadata,
            "nama_di_buku1": metadata.nama_di_buku1,
            "status_metadata": metadata.status_metadata,
        }
    )
    return hasil
```

Note: `FIELD_PUBLIK` (imported indirectly via `repo_indikator.FIELD_PUBLIK`
elsewhere in this same file) is untouched by this task — the admin list
uses `repo_indikator.cari()` for its filtering/pagination/sorting logic
(unchanged), but builds its own row shape via the new `_ringkas_admin()`
above instead of the existing `ringkas()` (which is scoped to
`FIELD_PUBLIK` only, for the public endpoint). Do not merge these two
functions — the public one intentionally hides internal-only fields
(`tim_pjk` individual names aside, things like `catatan_teknis`,
`link_metadata`, `status_rpjmd` are admin-only and must never leak into the
public `/indikator` response).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/integrasi/test_service_indikator_admin.py -v`
Expected: 11 passed.

- [ ] **Step 5: Run the full existing indikator test suite (regression check)**

Run: `python -m pytest tests/ -k indikator -v`
Expected: everything passes, including tests that existed before this task
(`koreksi_arah_baik` and friends) — this task only appends to
`services/indikator.py`, it doesn't touch any existing function.

- [ ] **Step 6: Lint, format, type-check**

```bash
ruff check backend/app/services/indikator.py tests/integrasi/test_service_indikator_admin.py
ruff format --check backend/app/services/indikator.py tests/integrasi/test_service_indikator_admin.py
mypy backend/app/services/indikator.py
```

Expected: all clean.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/indikator.py tests/integrasi/test_service_indikator_admin.py
git commit -m "$(cat <<'EOF'
Tambah service CRUD admin indikator dengan audit LogPerubahan/LogAktivitas

periksa_konsistensi_id() dipakai create dan update supaya kategori/nomor
tidak pernah menyimpang dari id_indikator (primary key, tidak bisa
diubah). arah_baik dan status_verifikasi sengaja dikecualikan dari
field yang bisa diedit form ini — tetap lewat jalur khusus yang sudah
ada.
EOF
)"
```

---

### Task 4: Router endpoints + API contract tests

**Files:**
- Modify: `backend/app/routers/admin.py`
- Test: `tests/api/test_admin_indikator.py` (new)

**Interfaces:**
- Consumes: everything from Task 1 (schemas) and Task 3 (service).
- Produces: five HTTP endpoints under `/api/v1/admin/indikator*`. Task 5
  (frontend `endpoints.js`) calls these five URLs by exact path and method.

**Context: test ordering matters in this file, on purpose.** The tests
below run against `tests/api/conftest.py`'s `client`/`db_uji` fixtures,
which are `scope="session"` — one shared SQLite file for every test in the
whole `tests/api/` run, seeded once by `_isi_benih()`. That means state
**persists across tests** in this file. The tests are written to run in
declaration order (create, then read, then update, then delete) and rely on
default pytest ordering (this repo has no `pytest-randomly` or similar
plugin installed — check `requirements-dev.txt` if you're unsure). Do not
reorder these tests, and do not extract them into a class with unrelated
tests interleaved.

- [ ] **Step 1: Write the failing tests**

Create `tests/api/test_admin_indikator.py`:

```python
"""Kontrak endpoint CRUD admin /api/v1/admin/indikator.

Memakai id "ISV-999" — sengaja dipilih supaya tidak bentrok dengan fixture
_isi_benih() (ISV-001, ISV-002, ISV-005, IUP-001, IUP-002) di conftest.py.
"""

from __future__ import annotations


def test_daftar_ditolak_tanpa_login(client):
    response = client.get("/api/v1/admin/indikator")
    assert response.status_code == 401


def test_buat_indikator_berhasil(client, auth):
    response = client.post(
        "/api/v1/admin/indikator",
        data={
            "id_indikator": "ISV-999",
            "kategori": "ISV",
            "nomor": 999,
            "nama_indikator": "Indikator Uji CRUD",
            "sumber_data": "BPS Uji",
            "definisi": "Definisi uji",
        },
        headers=auth,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {"status": "DIBUAT", "id_indikator": "ISV-999"}


def test_buat_indikator_id_tidak_konsisten_ditolak_422(client, auth):
    response = client.post(
        "/api/v1/admin/indikator",
        data={"id_indikator": "ISV-001", "kategori": "ISV", "nomor": 999, "nama_indikator": "X"},
        headers=auth,
    )
    assert response.status_code == 422


def test_buat_indikator_duplikat_ditolak_409(client, auth):
    response = client.post(
        "/api/v1/admin/indikator",
        data={"id_indikator": "ISV-999", "kategori": "ISV", "nomor": 999, "nama_indikator": "Duplikat"},
        headers=auth,
    )
    assert response.status_code == 409


def test_daftar_admin_menyertakan_indikator_baru(client, auth):
    response = client.get("/api/v1/admin/indikator", params={"q": "Indikator Uji CRUD"}, headers=auth)
    assert response.status_code == 200
    baris = response.json()["data"]
    assert any(item["id_indikator"] == "ISV-999" for item in baris)
    satu = next(item for item in baris if item["id_indikator"] == "ISV-999")
    assert satu["punya_nilai"] is False


def test_detail_admin_menyertakan_metadata(client, auth):
    response = client.get("/api/v1/admin/indikator/ISV-999", headers=auth)
    assert response.status_code == 200
    body = response.json()
    assert body["nama_indikator"] == "Indikator Uji CRUD"
    assert body["metadata"]["definisi"] == "Definisi uji"


def test_detail_admin_404_untuk_id_tidak_ada(client, auth):
    response = client.get("/api/v1/admin/indikator/ISV-000", headers=auth)
    assert response.status_code == 404


def test_perbarui_indikator_berhasil_dan_tercatat_di_log(client, auth):
    response = client.put(
        "/api/v1/admin/indikator/ISV-999",
        data={"kategori": "ISV", "nomor": 999, "nama_indikator": "Indikator Uji CRUD (Direvisi)"},
        headers=auth,
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "DIPERBARUI"}

    ulang = client.get("/api/v1/admin/indikator/ISV-999", headers=auth)
    assert ulang.json()["nama_indikator"] == "Indikator Uji CRUD (Direvisi)"

    log = client.get("/api/v1/admin/log", headers=auth)
    assert any(
        baris["id_indikator"] == "ISV-999" and baris["field"] == "nama_indikator" for baris in log.json()["data"]
    )


def test_perbarui_kategori_tidak_konsisten_ditolak_422(client, auth):
    response = client.put(
        "/api/v1/admin/indikator/ISV-999",
        data={"kategori": "IUP", "nomor": 999, "nama_indikator": "X"},
        headers=auth,
    )
    assert response.status_code == 422


def test_hapus_diblokir_saat_indikator_punya_nilai(client, auth):
    # ISV-001 dari _isi_benih() punya banyak baris nilai_indikator.
    response = client.delete("/api/v1/admin/indikator/ISV-001", headers=auth)
    assert response.status_code == 409


def test_hapus_berhasil_saat_tidak_punya_nilai(client, auth):
    response = client.delete("/api/v1/admin/indikator/ISV-999", headers=auth)
    assert response.status_code == 200
    assert response.json() == {"status": "DIHAPUS"}

    ulang = client.get("/api/v1/admin/indikator/ISV-999", headers=auth)
    assert ulang.status_code == 404


def test_hapus_404_untuk_id_tidak_ada(client, auth):
    response = client.delete("/api/v1/admin/indikator/ISV-999", headers=auth)
    assert response.status_code == 404
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/api/test_admin_indikator.py -v`
Expected: FAIL — 404s on every request (the routes don't exist yet), not
matching the expected status codes in the assertions.

- [ ] **Step 3: Implement the five endpoints**

Open `backend/app/routers/admin.py`. Change the import block at the top
from:

```python
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..deps import get_session, id_terautentikasi, wajib_peran
from ..models import Peran
from ..repositories import pengguna as repo_pengguna
from ..repositories import tata_kelola as repo_tata_kelola
from ..repositories.pengguna import ProfilPengguna
from ..schemas.admin import DaftarAkunResponse, LogResponse, PenggunaDibuatResponse
from ..schemas.umum import StatusResponse
from ..services import auth as svc_auth
from ..services import pengguna as svc
```

to:

```python
from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..deps import get_session, id_terautentikasi, wajib_peran
from ..models import Peran
from ..repositories import indikator as repo_indikator
from ..repositories import pengguna as repo_pengguna
from ..repositories import tata_kelola as repo_tata_kelola
from ..repositories.pengguna import ProfilPengguna
from ..schemas.admin import DaftarAkunResponse, LogResponse, PenggunaDibuatResponse
from ..schemas.indikator import (
    DaftarIndikatorAdminResponse,
    IndikatorAdminDetailResponse,
    IndikatorDibuatResponse,
    IndikatorFormBuat,
    IndikatorFormDasar,
)
from ..schemas.umum import StatusResponse
from ..services import auth as svc_auth
from ..services import indikator as svc_indikator
from ..services import pengguna as svc
```

Note the existing file already imports the user-management service as
`svc` (not renamed here to avoid touching every existing line below it) —
the new indikator service is imported as `svc_indikator` to avoid a name
collision. Every new function you add below uses `svc_indikator.*`, not
`svc.*`.

Now append these five endpoints to the end of the file (after the existing
`log_audit` function):

```python
@router.get("/admin/indikator", response_model=DaftarIndikatorAdminResponse)
def daftar_indikator_admin(
    q: str | None = None,
    kategori: list[str] | None = Query(None),
    kelompok: list[str] | None = Query(None),
    tim: list[str] | None = Query(None),
    sort: str = "id_indikator",
    order: Literal["asc", "desc"] = "asc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    admin: ProfilPengguna = Depends(hanya_admin),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return svc_indikator.daftar_admin(
        session, q=q, kategori=kategori, kelompok=kelompok, tim=tim, sort=sort, order=order, page=page, page_size=page_size
    )


@router.get("/admin/indikator/{id_indikator}", response_model=IndikatorAdminDetailResponse)
def detail_indikator_admin(
    id_indikator: str,
    admin: ProfilPengguna = Depends(hanya_admin),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    indikator = repo_indikator.ambil(session, id_indikator)
    if indikator is None:
        raise HTTPException(404, "Indikator tidak ditemukan")
    return svc_indikator.detail_admin(session, indikator)


@router.post("/admin/indikator", response_model=IndikatorDibuatResponse)
def buat_indikator_admin(
    form: Annotated[IndikatorFormBuat, Form()],
    admin: ProfilPengguna = Depends(hanya_admin),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    penolakan = svc_indikator.periksa_konsistensi_id(form.id_indikator, form.kategori, form.nomor)
    if penolakan:
        raise HTTPException(penolakan.kode, penolakan.pesan)
    try:
        indikator = svc_indikator.buat_indikator(session, form, pengguna_id=id_terautentikasi(admin))
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "id_indikator sudah dipakai") from exc
    return {"status": "DIBUAT", "id_indikator": indikator.id_indikator}


@router.put("/admin/indikator/{id_indikator}", response_model=StatusResponse)
def perbarui_indikator_admin(
    id_indikator: str,
    form: Annotated[IndikatorFormDasar, Form()],
    admin: ProfilPengguna = Depends(hanya_admin),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    indikator = repo_indikator.ambil(session, id_indikator)
    if indikator is None:
        raise HTTPException(404, "Indikator tidak ditemukan")
    penolakan = svc_indikator.periksa_konsistensi_id(id_indikator, form.kategori, form.nomor)
    if penolakan:
        raise HTTPException(penolakan.kode, penolakan.pesan)
    metadata = repo_indikator.ambil_metadata(session, id_indikator)
    return svc_indikator.perbarui_indikator(session, indikator, metadata, form, pengguna_id=id_terautentikasi(admin))


@router.delete("/admin/indikator/{id_indikator}", response_model=StatusResponse)
def hapus_indikator_admin(
    id_indikator: str,
    admin: ProfilPengguna = Depends(hanya_admin),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    indikator = repo_indikator.ambil(session, id_indikator)
    if indikator is None:
        raise HTTPException(404, "Indikator tidak ditemukan")
    penolakan = svc_indikator.periksa_penghapusan(session, id_indikator)
    if penolakan:
        raise HTTPException(penolakan.kode, penolakan.pesan)
    return svc_indikator.hapus_indikator(session, indikator, pengguna_id=id_terautentikasi(admin))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/api/test_admin_indikator.py -v`
Expected: 13 passed, in order.

- [ ] **Step 5: Full regression**

Run: `python -m pytest`
Expected: entire suite passes — this proves the new imports/endpoints in
`admin.py` didn't break the existing `/admin/pengguna`, `/admin/log`, etc.
endpoints in the same file.

- [ ] **Step 6: Architecture rule check (this is the step most likely to catch a mistake)**

Run: `python -m pytest tests/unit/test_arsitektur.py -v`
Expected: all pass. If `test_router_tidak_menyusun_query_sendiri` or
`test_tidak_ada_sql_mentah_di_router_dan_service` fails on `admin.py`, you
accidentally called `select()`/`insert()`/`text()` directly in a router
function instead of going through `repo_indikator`/`svc_indikator` — go
back and fix it there, don't add a `# noqa`-style suppression.

- [ ] **Step 7: Lint, format, type-check**

```bash
ruff check backend/app/routers/admin.py tests/api/test_admin_indikator.py
ruff format --check backend/app/routers/admin.py tests/api/test_admin_indikator.py
mypy backend/app/routers/admin.py
```

Expected: all clean.

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/admin.py tests/api/test_admin_indikator.py
git commit -m "$(cat <<'EOF'
Tambah endpoint CRUD admin /api/v1/admin/indikator

GET (daftar+detail), POST (buat), PUT (perbarui, full-replace), DELETE
(diblokir 409 bila masih punya nilai_indikator). Form pakai
Annotated[Model, Form()] karena field-nya banyak (~30), bukan Form()
skalar satu-satu seperti endpoint admin lain di berkas ini.
EOF
)"
```

---

### Task 5: Frontend API client functions

**Files:**
- Modify: `frontend/src/api/endpoints.js`

**Interfaces:**
- Consumes: `request`, `qs` from `./client` (already imported at the top of
  this file), the five endpoints from Task 4.
- Produces: `daftarIndikatorAdmin`, `detailIndikatorAdmin`,
  `buatIndikatorAdmin`, `perbaruiIndikatorAdmin`, `hapusIndikatorAdmin` —
  Task 6 (`IndikatorManager.jsx`) imports all five by exact name from
  `../../api/endpoints`.

No automated test for this task — it's five one-line functions with no
branching logic, in a file with no existing test coverage of its own
(`endpoints.js` is exercised indirectly by every page's tests, and this
repo doesn't have a dedicated test file for it — check
`frontend/src/api/client.test.js` if you want confirmation: it tests
`client.js`, not `endpoints.js`). Task 6's component test exercises these
functions through mocking, which is where the real coverage comes from.

- [ ] **Step 1: Add the five functions**

Open `frontend/src/api/endpoints.js`. Find this line near the end of the
"tata kelola" section:

```js
export const koreksiArahBaik = (id, form) =>
  request(`${V1}/arah-baik/${id}`, {method: 'PUT', body: form, ...wajib})
```

Add the five new lines directly after it (before `export const pratinjauUnggahan = ...`):

```js
export const daftarIndikatorAdmin = params => request(denganQuery(`${V1}/admin/indikator`, params), wajib)
export const detailIndikatorAdmin = id => request(`${V1}/admin/indikator/${id}`, wajib)
export const buatIndikatorAdmin = form =>
  request(`${V1}/admin/indikator`, {method: 'POST', body: form, ...wajib})
export const perbaruiIndikatorAdmin = (id, form) =>
  request(`${V1}/admin/indikator/${id}`, {method: 'PUT', body: form, ...wajib})
export const hapusIndikatorAdmin = id =>
  request(`${V1}/admin/indikator/${id}`, {method: 'DELETE', ...wajib})
```

- [ ] **Step 2: Lint**

```bash
cd frontend && pnpm lint
```

Expected: clean (no new errors — this file already passes lint before your
change; if it doesn't after, you introduced a syntax issue in the added
lines).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/endpoints.js
git commit -m "$(cat <<'EOF'
Tambah fungsi client untuk lima endpoint CRUD admin indikator
EOF
)"
```

---

### Task 6: `IndikatorManager.jsx` — table + create/edit form

**Files:**
- Create: `frontend/src/components/admin/IndikatorManager.jsx`
- Test: `frontend/src/components/admin/IndikatorManager.test.jsx` (new)

**Interfaces:**
- Consumes: the five functions from Task 5
  (`../../api/endpoints`), `Panel`/`EmptyState` from `../../ui`
  (already exist).
- Produces: `export function IndikatorManager()` — a self-contained
  component that fetches its own data (does not take `rows`/`onX` props
  like `SubmissionTable` does), because unlike `SubmissionTable` this
  component owns a full CRUD lifecycle, not just a display list. Task 7
  (`AdminPage.jsx`) renders `<IndikatorManager/>` with **no props**.

**Context: why this component fetches its own data instead of receiving
props from `AdminPage.jsx` (unlike every other admin component today).**
`AdminPage.jsx` already manages nine pieces of `useState` for five
different concerns (accounts, submissions, logs, evidence, password reset).
Adding "indikator list + selected row for editing + create/edit modal open
state" to that same component would make an already-dense 400-line file
harder to reason about, and none of that state is needed by anything else
on the page. Keeping it self-contained here is a deliberate boundary, not
an oversight — match this repo's own instruction to "design units with
clear boundaries" from its own conventions, not the flatter pattern the
older `SubmissionTable` happens to use.

**Context: why `kategori`/`nomor` render as read-only when editing.** HTML
disables **excludes an input from form submission entirely** — if you use
`disabled` on the `kategori`/`nomor` inputs in edit mode, the browser won't
include them in the submitted `FormData` at all, and the backend's
`IndikatorFormDasar.kategori`/`.nomor` have no default value (they're
required), so the request would fail validation with "field required",
not the intended "these are shown for reference." The fix used below:
render them as `<input type="hidden">` (still submitted, invisible) plus a
plain read-only `<span>` for display — `readOnly` (not `disabled`) would
also work for the `<input type="number">` for `nomor`, but there's no
equivalent for a `<select>`, so the hidden-input approach is used for both
so edit mode is consistent.

**Context: why checkboxes for `is_proxy`/`perlu_verifikasi_manual` need no
extra JS.** An unchecked HTML checkbox is omitted from `FormData` entirely
(native browser behavior) — and the backend's `IndikatorFormDasar` gives
both those fields a Pydantic default of `False`. Missing key -> Pydantic
default -> `False`. Checked -> key present with value `"on"` -> coerced to
`True`. This is exactly checkbox semantics with zero extra code; do not add
an `onChange` handler that manually tracks these as JS state.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/admin/IndikatorManager.test.jsx`:

```jsx
/* @vitest-environment jsdom */
import {afterEach, describe, expect, it, vi} from 'vitest'
import {createRoot} from 'react-dom/client'
import {act} from 'react'

import {IndikatorManager} from './IndikatorManager'
import * as endpoints from '../../api/endpoints'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

let root
let wadah

function render(element) {
  wadah = document.createElement('div')
  document.body.appendChild(wadah)
  root = createRoot(wadah)
  act(() => root.render(element))
  return wadah
}

afterEach(() => {
  if (root) act(() => root.unmount())
  wadah?.remove()
  root = undefined
  vi.restoreAllMocks()
})

const baris = {
  id_indikator: 'ISV-999',
  kategori: 'ISV',
  nomor: 999,
  nama_indikator: 'Indikator Uji',
  kelompok: 'Kelompok Uji',
  status_ketersediaan: 'Tersedia',
  punya_nilai: false,
}

describe('IndikatorManager', () => {
  it('menampilkan baris dari daftarIndikatorAdmin', async () => {
    vi.spyOn(endpoints, 'daftarIndikatorAdmin').mockResolvedValue({data: [baris], total: 1, page: 1, page_size: 25})
    render(<IndikatorManager />)
    await act(async () => {})
    expect(wadah.textContent).toContain('Indikator Uji')
  })

  it('menonaktifkan tombol hapus saat indikator punya nilai', async () => {
    vi.spyOn(endpoints, 'daftarIndikatorAdmin').mockResolvedValue({
      data: [{...baris, punya_nilai: true}],
      total: 1,
      page: 1,
      page_size: 25,
    })
    render(<IndikatorManager />)
    await act(async () => {})
    const tombolHapus = wadah.querySelector('[data-uji="hapus-ISV-999"]')
    expect(tombolHapus.disabled).toBe(true)
  })

  it('memanggil buatIndikatorAdmin saat form tambah disubmit', async () => {
    vi.spyOn(endpoints, 'daftarIndikatorAdmin').mockResolvedValue({data: [], total: 0, page: 1, page_size: 25})
    const buat = vi.spyOn(endpoints, 'buatIndikatorAdmin').mockResolvedValue({status: 'DIBUAT', id_indikator: 'ISV-999'})
    render(<IndikatorManager />)
    await act(async () => {})

    wadah.querySelector('[data-uji="tombol-tambah"]').click()
    await act(async () => {})

    const form = wadah.querySelector('[data-uji="form-indikator"]')
    form.querySelector('[name="id_indikator"]').value = 'ISV-999'
    form.querySelector('[name="kategori"]').value = 'ISV'
    form.querySelector('[name="nomor"]').value = '999'
    form.querySelector('[name="nama_indikator"]').value = 'Indikator Uji'

    await act(async () => form.requestSubmit())

    expect(buat).toHaveBeenCalledTimes(1)
    expect(buat.mock.calls[0][0].get('id_indikator')).toBe('ISV-999')
  })

  it('memanggil hapusIndikatorAdmin saat tombol hapus ditekan dan dikonfirmasi', async () => {
    vi.spyOn(endpoints, 'daftarIndikatorAdmin').mockResolvedValue({data: [baris], total: 1, page: 1, page_size: 25})
    const hapus = vi.spyOn(endpoints, 'hapusIndikatorAdmin').mockResolvedValue({status: 'DIHAPUS'})
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<IndikatorManager />)
    await act(async () => {})

    await act(async () => wadah.querySelector('[data-uji="hapus-ISV-999"]').click())

    expect(hapus).toHaveBeenCalledWith('ISV-999')
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && pnpm vitest run src/components/admin/IndikatorManager.test.jsx`
Expected: FAIL — `Failed to resolve import "./IndikatorManager"`.

- [ ] **Step 3: Write the component**

Create `frontend/src/components/admin/IndikatorManager.jsx`:

```jsx
import {useEffect, useState} from 'react'
import {Pencil, Plus, Trash2} from 'lucide-react'
import {EmptyState, Panel} from '../../ui'
import {
  buatIndikatorAdmin,
  daftarIndikatorAdmin,
  detailIndikatorAdmin,
  hapusIndikatorAdmin,
  perbaruiIndikatorAdmin,
} from '../../api/endpoints'

/* Form gabungan create+edit: dikunci dengan `key` (lihat pemakaian di bawah)
   supaya React membuat instance <form> baru tiap kali baris yang diedit
   berganti atau berpindah ke mode "tambah baru" — cara termurah untuk
   mereset isian tak-terkendali (uncontrolled) tanpa useEffect sinkronisasi. */
function FormIndikator({editing, onCancel, onSaved, onError}) {
  const [saving, setSaving] = useState(false)
  const isEdit = Boolean(editing)

  const submit = async event => {
    event.preventDefault()
    setSaving(true)
    const form = new FormData(event.currentTarget)
    try {
      if (isEdit) await perbaruiIndikatorAdmin(editing.id_indikator, form)
      else await buatIndikatorAdmin(form)
      onSaved()
    } catch (error) {
      onError(error.detail || error.message || 'Gagal menyimpan indikator')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="panel role-form" data-uji="form-indikator" onSubmit={submit}>
      <h3>{isEdit ? `Edit ${editing.id_indikator}` : 'Tambah indikator baru'}</h3>

      <fieldset>
        <legend>Identitas & klasifikasi</legend>
        {isEdit
          ? <div className="form-pair">
              <input type="hidden" name="kategori" value={editing.kategori} />
              <input type="hidden" name="nomor" value={editing.nomor} />
              <span className="locked-field">{editing.id_indikator}</span>
            </div>
          : <div className="form-pair">
              <input name="id_indikator" placeholder="mis. ISV-087" required defaultValue="" />
              <select name="kategori" defaultValue="ISV">
                <option value="ISV">ISV</option>
                <option value="IUP">IUP</option>
              </select>
              <input name="nomor" type="number" min="1" placeholder="Nomor urut" required />
            </div>}
        <input name="nama_indikator" placeholder="Nama indikator" required defaultValue={editing?.nama_indikator || ''} />
        <input name="nama_asli" placeholder="Nama asli (RPJPD)" defaultValue={editing?.nama_asli || ''} />
        <input name="kode_indikator" placeholder="Kode indikator" defaultValue={editing?.kode_indikator || ''} />
        <input name="kelompok" placeholder="Kelompok / pilar" defaultValue={editing?.kelompok || ''} />
        <input name="arah_pembangunan" placeholder="Arah pembangunan (ISV)" defaultValue={editing?.arah_pembangunan || ''} />
        <input name="arah_ie" placeholder="Arah Indonesia Emas (IUP)" defaultValue={editing?.arah_ie || ''} />
        <input name="sasaran_visi" placeholder="Sasaran visi" defaultValue={editing?.sasaran_visi || ''} />
        <input name="misi_agenda" placeholder="Misi / agenda" defaultValue={editing?.misi_agenda || ''} />
        <input name="indikator_induk" placeholder="Indikator induk" defaultValue={editing?.indikator_induk || ''} />
        <input name="kelompok_makro" placeholder="Kelompok makro" defaultValue={editing?.kelompok_makro || ''} />
        <input name="satuan" placeholder="Satuan (mis. Persen (%))" defaultValue={editing?.satuan || ''} />
        <label className="checkbox-field">
          <input type="checkbox" name="is_proxy" defaultChecked={editing?.is_proxy || false} />
          <span>Indikator proxy</span>
        </label>
        <input name="nama_proxy" placeholder="Nama indikator proxy (bila ada)" defaultValue={editing?.nama_proxy || ''} />
      </fieldset>

      <fieldset>
        <legend>Kepemilikan & ketersediaan</legend>
        <input name="penghasil" placeholder="Penghasil indikator" defaultValue={editing?.penghasil || ''} />
        <input name="kl_pengampu" placeholder="K/L/D/I pengampu" defaultValue={editing?.kl_pengampu || ''} />
        <input name="opd_pengampu" placeholder="OPD pengampu (Kaltara)" defaultValue={editing?.opd_pengampu || ''} />
        <input name="tim_pjk" placeholder="Tim PJK" defaultValue={editing?.tim_pjk || ''} />
        <input name="sumber_data" placeholder="Sumber data" defaultValue={editing?.sumber_data || ''} />
        <input name="frekuensi" placeholder="Frekuensi" defaultValue={editing?.frekuensi || ''} />
        <input name="status_ketersediaan" placeholder="Status ketersediaan data" defaultValue={editing?.status_ketersediaan || ''} />
        <input name="status_metadata" placeholder="Status metadata" defaultValue={editing?.status_metadata || ''} />
        <input name="periode_data" placeholder="Periode data" defaultValue={editing?.periode_data || ''} />
        <input name="tahun_terakhir" type="number" placeholder="Tahun data terakhir" defaultValue={editing?.tahun_terakhir || ''} />
        <input name="status_rpjmd" placeholder="Status RPJMD" defaultValue={editing?.status_rpjmd || ''} />
        <input name="kode_sdgs" placeholder="Kode SDGs" defaultValue={editing?.kode_sdgs || ''} />
        <input name="link_metadata" placeholder="Tautan metadata" defaultValue={editing?.link_metadata || ''} />
        <input name="link_publikasi" placeholder="Tautan publikasi" defaultValue={editing?.link_publikasi || ''} />
        <input name="link_data" placeholder="Tautan data" defaultValue={editing?.link_data || ''} />
        <textarea name="catatan_teknis" placeholder="Catatan teknis" defaultValue={editing?.catatan_teknis || ''} />
      </fieldset>

      <fieldset>
        <legend>Metadata & definisi</legend>
        <textarea name="definisi" placeholder="Definisi" defaultValue={editing?.metadata?.definisi || ''} />
        <textarea name="interpretasi" placeholder="Interpretasi" defaultValue={editing?.metadata?.interpretasi || ''} />
        <textarea name="rumus" placeholder="Rumus (keterangan notasi)" defaultValue={editing?.metadata?.rumus || ''} />
        <textarea name="rumus_mentah" placeholder="Rumus perhitungan (mentah)" defaultValue={editing?.metadata?.rumus_mentah || ''} />
        <input name="rumus_latex" placeholder="Rumus (LaTeX)" defaultValue={editing?.metadata?.rumus_latex || ''} />
        <input name="halaman_sumber" placeholder="Halaman sumber (Buku 1)" defaultValue={editing?.metadata?.halaman_sumber || ''} />
        <input name="sumber_metadata" placeholder="Sumber metadata" defaultValue={editing?.metadata?.sumber_metadata || ''} />
        <input name="nama_di_buku1" placeholder="Nama di Buku 1" defaultValue={editing?.metadata?.nama_di_buku1 || ''} />
        <label className="checkbox-field">
          <input type="checkbox" name="perlu_verifikasi_manual" defaultChecked={editing?.metadata?.perlu_verifikasi_manual || false} />
          <span>Perlu verifikasi manual</span>
        </label>
      </fieldset>

      <div className="row-actions">
        <button type="button" onClick={onCancel} disabled={saving}>Batal</button>
        <button type="submit" disabled={saving}>{saving ? 'Menyimpan...' : 'Simpan'}</button>
      </div>
    </form>
  )
}

export function IndikatorManager() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(null) // null = tertutup, {} tidak dipakai — 'baru' via flag terpisah
  const [creating, setCreating] = useState(false)
  const [message, setMessage] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const result = await daftarIndikatorAdmin({page_size: 200})
      setRows(result.data)
    } catch (error) {
      setMessage(error.detail || error.message || 'Gagal memuat daftar indikator')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const openEdit = async row => {
    try {
      const detail = await detailIndikatorAdmin(row.id_indikator)
      setEditing(detail)
      setCreating(false)
    } catch (error) {
      setMessage(error.detail || error.message || 'Gagal memuat detail indikator')
    }
  }

  const remove = async row => {
    if (!confirm(`Hapus indikator ${row.id_indikator}? Tindakan ini tidak dapat dibatalkan.`)) return
    try {
      await hapusIndikatorAdmin(row.id_indikator)
      setMessage(`Indikator ${row.id_indikator} dihapus.`)
      load()
    } catch (error) {
      setMessage(error.detail || error.message || 'Gagal menghapus indikator')
    }
  }

  const closeForm = () => {
    setEditing(null)
    setCreating(false)
  }

  const saved = () => {
    setMessage(editing ? `Indikator ${editing.id_indikator} diperbarui.` : 'Indikator baru ditambahkan.')
    closeForm()
    load()
  }

  return (
    <Panel
      delay={40}
      kicker="Manajemen indikator"
      title="Daftar indikator"
      desc="Buat, ubah, atau hapus indikator dan metadatanya."
      actions={
        <button data-uji="tombol-tambah" onClick={() => { setCreating(true); setEditing(null) }}>
          <Plus size={16} /> Tambah indikator
        </button>
      }
    >
      {message && <p className="form-hint">{message}</p>}

      {(creating || editing) &&
        <FormIndikator editing={editing} key={editing ? editing.id_indikator : 'baru'} onCancel={closeForm} onSaved={saved} onError={setMessage} />}

      {loading
        ? <p>Memuat...</p>
        : rows.length
          ? <div className="table-scroll">
              <table className="workspace-table">
                <thead>
                  <tr><th>ID</th><th>Nama</th><th>Kategori</th><th>Kelompok</th><th>Status ketersediaan</th><th>Aksi</th></tr>
                </thead>
                <tbody>
                  {rows.map(row =>
                    <tr key={row.id_indikator}>
                      <td><b>{row.id_indikator}</b></td>
                      <td>{row.nama_indikator}</td>
                      <td>{row.kategori}</td>
                      <td>{row.kelompok || '—'}</td>
                      <td>{row.status_ketersediaan || '—'}</td>
                      <td>
                        <div className="row-actions">
                          <button onClick={() => openEdit(row)} aria-label={`Edit ${row.id_indikator}`}>
                            <Pencil size={14} />
                          </button>
                          <button
                            data-uji={`hapus-${row.id_indikator}`}
                            onClick={() => remove(row)}
                            disabled={row.punya_nilai}
                            title={row.punya_nilai ? 'Masih punya histori nilai; tidak dapat dihapus' : 'Hapus indikator'}
                            aria-label={`Hapus ${row.id_indikator}`}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          : <EmptyState title="Belum ada indikator" desc="Tambahkan indikator pertama lewat tombol di atas." />}
    </Panel>
  )
}
```

A few things worth double-checking as you write this, because they're easy
to get subtly wrong:

- `editing` holds the **full detail object** (from `detailIndikatorAdmin`,
  which nests `metadata`), not the row object from the list (which has no
  `metadata` key). The `openEdit` function above fetches detail before
  opening the form specifically so `editing?.metadata?.definisi` etc. have
  something to read.
- The `key={editing ? editing.id_indikator : 'baru'}` on `<FormIndikator>`
  is what makes the uncontrolled `defaultValue`/`defaultChecked` inputs
  reset correctly when you switch from editing one row to another, or from
  editing to creating — without it, React would reuse the same DOM `<input>`
  nodes and their stale values, since none of these inputs are controlled.
- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend && pnpm vitest run src/components/admin/IndikatorManager.test.jsx`
Expected: 4 passed.

- [ ] **Step 5: Lint**

```bash
cd frontend && pnpm lint
```

Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/admin/IndikatorManager.jsx frontend/src/components/admin/IndikatorManager.test.jsx
git commit -m "$(cat <<'EOF'
Tambah komponen IndikatorManager: tabel + form create/edit indikator

Form dibagi 3 fieldset (identitas, kepemilikan, metadata) supaya ~30
field tidak jadi satu scroll raksasa. kategori/nomor jadi input hidden
saat edit (bukan disabled) supaya tetap ikut terkirim di FormData.
EOF
)"
```

---

### Task 7: Mount into `AdminPage.jsx` + final regression

**Files:**
- Modify: `frontend/src/pages/AdminPage.jsx`

**Interfaces:**
- Consumes: `IndikatorManager` from Task 6.
- Produces: nothing further depends on this — last task in this plan.

- [ ] **Step 1: Import the component**

Open `frontend/src/pages/AdminPage.jsx`. Change this line near the top:

```jsx
import {SubmissionTable} from '../components/admin/SubmissionTable'
```

to:

```jsx
import {IndikatorManager} from '../components/admin/IndikatorManager'
import {SubmissionTable} from '../components/admin/SubmissionTable'
```

- [ ] **Step 2: Render it in the admin-only section**

Find this block (the last `ADMIN`-only panel in the file, the audit log):

```jsx
    {me?.peran==='ADMIN'&&
      <Panel delay={40} kicker="Audit nilai" title="Jejak perubahan terverifikasi">
        <div className="table-scroll">
          <table className="workspace-table">
            <thead>
              <tr><th>Waktu</th><th>Pengguna</th><th>Indikator</th><th>Nilai lama</th><th>Nilai baru</th><th>Sumber</th></tr>
            </thead>
            <tbody>
              {logs.map(row=>
                <tr key={row.id}>
                  <td>{dateText(row.waktu)}</td>
                  <td>{row.username||'sistem'}</td>
                  <td>{row.id_indikator}</td>
                  <td>{row.nilai_lama??'—'}</td>
                  <td>{row.nilai_baru??'—'}</td>
                  <td>{row.sumber_perubahan}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>}
```

Add `<IndikatorManager/>` directly after it (still inside the
`{me?.peran==='ADMIN'&&<>...}` fragment from higher up in the file — check
that this block is still inside that fragment before you add to it; if
you're not sure, search the file for the opening `{me?.peran==='ADMIN'&&<>`
a few dozen lines above the block you just found, and confirm there's no
closing `</>}` between it and here):

```jsx
    {me?.peran==='ADMIN'&&
      <Panel delay={40} kicker="Audit nilai" title="Jejak perubahan terverifikasi">
        <div className="table-scroll">
          <table className="workspace-table">
            <thead>
              <tr><th>Waktu</th><th>Pengguna</th><th>Indikator</th><th>Nilai lama</th><th>Nilai baru</th><th>Sumber</th></tr>
            </thead>
            <tbody>
              {logs.map(row=>
                <tr key={row.id}>
                  <td>{dateText(row.waktu)}</td>
                  <td>{row.username||'sistem'}</td>
                  <td>{row.id_indikator}</td>
                  <td>{row.nilai_lama??'—'}</td>
                  <td>{row.nilai_baru??'—'}</td>
                  <td>{row.sumber_perubahan}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>}

    {me?.peran==='ADMIN'&&<IndikatorManager/>}
```

Note this repeats the `{me?.peran==='ADMIN'&&...}` guard rather than
nesting inside the existing `<>...</>` fragment that starts higher up in
the file (around the "Pengguna" panel) — that's deliberate and matches how
the file already mixes both styles (the audit-log panel above is a
**separate** top-level `{me?.peran==='ADMIN'&&...}` expression too, not
nested in the earlier fragment). Match that existing pattern rather than
threading a new component into an unrelated JSX fragment several dozen
lines away.

- [ ] **Step 3: Manual browser check**

Run the dev servers:

```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
cd frontend && pnpm dev
```

Open the frontend dev URL, log in as an admin account (use the credentials
created by `python -m backend.app.cli seed --tampilkan-sandi` if you don't
already have one), and confirm:
- A "Daftar indikator" panel appears below "Jejak perubahan terverifikasi".
- Clicking "Tambah indikator" opens the create form with three fieldsets.
- Submitting a create with a fresh id (e.g. `ISV-995`) succeeds and the new
  row appears in the table.
- Clicking the pencil icon on that row opens the edit form pre-filled with
  its values (including anything you typed in the Metadata fieldset).
- Clicking the trash icon on an indicator that has recorded values (e.g.
  any of the real seeded indicators, if Task A's plan has been run) is
  disabled with a tooltip; clicking it on the `ISV-995` row you just
  created (which has no values) prompts a confirm dialog and, on
  confirming, removes the row.

If anything in this manual pass doesn't match, stop and fix it before
moving on — this is the step that actually proves the feature works
end-to-end, not just that individual layers pass their own tests in
isolation. Report explicitly if you skip this step (e.g. no display
available in your environment) rather than silently omitting it.

- [ ] **Step 4: Full frontend regression**

```bash
cd frontend && pnpm lint && pnpm test && pnpm build
```

Expected: all three clean/passing. `pnpm build` in particular catches
JSX syntax mistakes that `pnpm lint` alone sometimes misses.

- [ ] **Step 5: Full backend regression**

```bash
python -m pytest --cov=backend/app --cov=src --cov-fail-under=80
ruff check .
ruff format --check .
mypy backend src
```

Expected: all clean/passing, coverage still ≥ 80%.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/AdminPage.jsx
git commit -m "$(cat <<'EOF'
Pasang IndikatorManager di AdminPage

Panel baru khusus ADMIN, ditempatkan setelah jejak perubahan
terverifikasi. AdminPage sendiri tidak menampung logic tabel/form —
komponennya mengambil datanya sendiri.
EOF
)"
```

---

## Final check for this plan

```bash
python -m pytest --cov=backend/app --cov=src --cov-fail-under=80
ruff check . && ruff format --check . && mypy backend src
cd frontend && pnpm lint && pnpm test && pnpm build
```

All must be clean. If this plan was implemented together with the
seed-indikator plan (`2026-08-27-seed-indikator.md`), also re-run that
plan's final check — the two together are what makes "fresh deploy has 86
real indicators, admin can manage them from the web" actually true
end-to-end.
