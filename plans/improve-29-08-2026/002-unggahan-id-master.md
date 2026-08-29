# 002 — Tolak unggahan massal tanpa irisan ID master

Baca `plans/improve-29-08-2026/README.md` dan `AGENTS.md` sebelum mulai.

**Tujuan:** `terapkan()` menolak unggahan jika tidak satu pun ID di staging cocok dengan tabel `indikator` yang hidup. Status unggahan **tidak** menjadi `DISETUJUI`. `indicator_id()` dan pipeline ETL **tidak** diubah.

**Ditulis terhadap:** commit `8b3ae9a`.

**Cek dulu:**

```text
git diff --stat 8b3ae9a..HEAD -- backend/app/services/unggahan.py backend/app/routers/unggahan.py backend/app/schemas/unggahan.py src/etl/common.py tests/
```

## Ringkasan

| | |
|---|---|
| Prioritas | P1 |
| Perkiraan | sekitar sehari |
| Risiko ubahan | sedang |
| Bergantung pada | tidak ada (jangan dicampur seed-indikator) |
| Cabang | `fix/unggahan-id-master` |
| Pesan commit | `Tolak unggahan massal tanpa irisan ID master` |

## Mengapa ini penting

Daftar hidup memakai ID master (`ISV-001`). Pipeline ETL yang masih dipanggil unggahan massal (`src.etl.pipeline.run`) membentuk ID lewat `indicator_id()` sebagai `ISV-01` (`:02d`). Irisannya **nol** — lihat `docs/refactoring/CATATAN-PELAKSANAAN.md` Temuan 1.

`terapkan()` melewati ID yang tidak dikenal lalu tetap menandai unggahan `DISETUJUI` meski `jumlah == 0`. Admin mengira angka provinsi berubah; faktanya tidak.

## Keadaan sekarang

- `src/etl/common.py` sekitar 51–57:

```python
def indicator_id(category: Any, number: Any) -> str | None:
    cat = (clean_text(category) or "").upper()
    num = parse_angka(number)
    if cat not in {"ISV", "IUP"} or num is None:
        return None
    return f"{cat}-{int(num):02d}"
```

- `backend/app/routers/unggahan.py` sekitar 36–51 — pratinjau mengarsipkan xlsx, menjalankan ETL, `susun_diff`, lalu menyimpan `UnggahanExcel` berstatus `MENUNGGU_PERSETUJUAN`. `BerkasTidakValid` → 422 (pratinjau) atau 409 (setujui).
- `backend/app/services/unggahan.py` sekitar 73–86 — `_baca_staging` membaca SQLite dengan SQL tetap: `SELECT id_indikator,nama_indikator FROM indikator` dan `SELECT id_indikator,tahun,jenis,nilai FROM nilai_indikator`.
- `unggahan.py` sekitar 117–161 — `terapkan`: `if id_indikator not in dikenal: continue`, lalu `unggahan.status = DISETUJUI` meski nol baris.
- Model `UnggahanExcel` (`backend/app/models/tata_kelola.py` sekitar 117–130): `nama_file_asli`, `path_arsip`, `checksum_sha256`, `status`, `ringkasan_diff`, `pengguna_id`.
- Path staging: `Path(unggahan.path_arsip).with_suffix(".stage.db")`.
- `backend/app/schemas/unggahan.py` — `DiffUnggahan` model tertutup: `indikator_baru`, `indikator_hilang`, `nilai_berubah`. Kunci tambahan **dibuang** kecuali field ditambahkan.
- Enum jenis: `"realisasi"` / `"target"` (huruf kecil).
- Fixture sesi tes: `tests/conftest.py` → `session` (skema Alembic, di-rollback).
- Pola indikator uji: `tests/integrasi/test_alur_verifikasi.py` fixture `dunia`.

Jangan ubah `indicator_id()` atau menulis ulang ETL. Pengaman ada di layanan unggahan.

## Cakupan

**Boleh diubah:**
- `backend/app/services/unggahan.py` — tolak apply jika irisan ID kosong; jangan set `DISETUJUI`. Tambah `id_tidak_dikenal` pada dict diff.
- `backend/app/schemas/unggahan.py` — `id_tidak_dikenal: list[str] = []` pada `DiffUnggahan`.
- `tests/integrasi/test_unggahan_id.py` (berkas baru).

**Jangan diubah:**
- `src/etl/pipeline.py`, `indicator_id()`, `workbook.yaml`.
- Fixture JSON seed-indikator.
- Pesan galat ETL yang membocorkan `{exc}` (di luar pengaman ini).
- Batch upsert.
- `backend/app/routers/unggahan.py` — `BerkasTidakValid` sudah dipetakan; biarkan router.

## Langkah

### 1. Tes yang gagal dulu

Buat `tests/integrasi/test_unggahan_id.py`.

Pembantu, dengan `session` dan `tmp_path`:

1. Sisip `Indikator(id_indikator="ISV-001", kategori="ISV", nama_indikator="X", is_proxy=False, status_verifikasi="DISETUJUI")` — kolom minimum seperti fixture `dunia` di `test_alur_verifikasi.py`. `session.flush()`.
2. `arsip = tmp_path / "uji.xlsx"`; `arsip.write_bytes(b"PK")`.
3. Tulis SQLite staging di `arsip.with_suffix(".stage.db")`:

```sql
CREATE TABLE indikator (id_indikator TEXT, nama_indikator TEXT);
CREATE TABLE nilai_indikator (id_indikator TEXT, tahun INTEGER, jenis TEXT, nilai REAL);
INSERT INTO indikator VALUES ('ISV-01', 'lama');
INSERT INTO nilai_indikator VALUES ('ISV-01', 2023, 'realisasi', 1.0);
```

4. Objek `UnggahanExcel(nama_file_asli="uji.xlsx", path_arsip=str(arsip), checksum_sha256="0"*64, status="MENUNGGU_PERSETUJUAN")`. `terapkan` hanya membaca staging, bukan xlsx.

Tes:
- `test_terapkan_id_lama_tanpa_irisan_ditolak`: `terapkan(...)` memunculkan `BerkasTidakValid`; tidak ada baris `nilai_indikator`; status unggahan **bukan** `DISETUJUI`.
- `test_terapkan_id_master_menulis_nilai`: staging `ISV-001` / `realisasi` / 2023 / 9.0 → kembalian 1; baris hidup ada.
- `test_susun_diff_mencatat_id_tidak_dikenal` (setelah langkah 3): `diff["id_tidak_dikenal"]` berisi `"ISV-01"`.

Impor `terapkan`, `susun_diff`, `BerkasTidakValid` dari `backend.app.services.unggahan`. `wilayah_kode` hasil apply adalah `KODE_PROVINSI` (`"65"`).

**Cek:**

```text
python -m pytest tests/integrasi/test_unggahan_id.py::test_terapkan_id_lama_tanpa_irisan_ditolak -q
```

Harus **GAGAL** (sekarang mengembalikan 0 dan men-set DISETUJUI). Kalau sudah raise, berhenti.

### 2. Pengaman di `terapkan`

Setelah `_baca_staging` dan `dikenal = {...}`:

```python
id_staging = {kunci[0] for kunci in nilai_baru}
if not nilai_baru:
    raise BerkasTidakValid("Berkas staging tidak memuat nilai indikator")
if not (id_staging & dikenal):
    raise BerkasTidakValid(
        "Tidak ada ID indikator yang cocok dengan daftar master. "
        "Unggahan memakai skema ID lama (ISV-01) atau sheet yang salah."
    )
```

Jangan set `DISETUJUI` sebelum pengaman. Berkas campuran (sebagian ID dikenal) boleh tetap menerapkan subset yang dikenal; irisan kosong wajib gagal.

**Cek:** dua tes `terapkan` lulus.

### 3. Pratinjau menampilkan ID yang tidak dikenal

Di `susun_diff`, tambah ke dict `diff`:

```python
"id_tidak_dikenal": sorted({kunci[0] for kunci in nilai_baru} - set(indikator_lama)),
```

Di `DiffUnggahan` (`backend/app/schemas/unggahan.py`):

```python
id_tidak_dikenal: list[str] = []
```

Tanpa field ini, Pydantic membuang kuncinya.

**Cek:**

```text
python -m pytest tests/integrasi/test_unggahan_id.py tests/api/test_kontrak_openapi.py tests/unit/test_arsitektur.py -q
```

Semua lulus. Tes arsitektur harus tetap hijau: jangan menambah `text(` SQLAlchemy di service (sqlite `execute("SELECT ...")` yang sudah ada boleh tetap).

```text
ruff check backend/app/services/unggahan.py backend/app/schemas/unggahan.py tests/integrasi/test_unggahan_id.py
```

## Selesai bila semua ini benar

- [ ] `python -m pytest tests/integrasi/test_unggahan_id.py -q` kode keluar 0
- [ ] `terapkan` tidak bisa sukses jika irisan ID kosong
- [ ] `git diff -- src/etl/common.py` kosong (`indicator_id` tidak berubah)
- [ ] `DiffUnggahan` punya `id_tidak_dikenal`
- [ ] `ruff check` pada berkas yang disentuh kode keluar 0
- [ ] Baris 002 di `plans/improve-29-08-2026/README.md` menjadi `DONE`

## Berhenti dan tanya

- Skema staging di `_baca_staging` tidak lagi dua tabel itu.
- Produk ingin **memetakan** `ISV-01` → `ISV-001` otomatis — itu desain lain; jangan membuat tabel pemetaan.
- Terasa perlu mengubah `workbook.yaml` atau format ID ETL — di luar cakupan.

## Catatan untuk peninjau

Berkas campuran tetap menerapkan ID yang dikenal. Hanya irisan kosong yang fatal. Seed-indikator menulis `ISV-001` langsung, tidak lewat jalur ETL ini.
