# 003 — Pisahkan seri tampilan beranda dari seri teramati

Baca `plans/improve-29-08-2026/README.md` dan `AGENTS.md` sebelum mulai.

**Tujuan:** Capaian, insight (seri YoY), dan analitik memakai tahun yang benar-benar ada. Beranda **tetap** mengisi celah 2021–2025 (kartu sudah menampilkan `keterangan`).

**Ditulis terhadap (awal):** `8b3ae9a`.
**Disesuaikan terhadap:** `4a7939f` (29 Agustus 2026). Berkas seri/analitik **tidak** berubah di batch seed/CRUD/unggah; bug isian celah masih ada.

**Cek dulu:**

```text
git diff --stat 4a7939f..HEAD -- backend/app/repositories/nilai.py backend/app/services/analitik.py backend/app/services/capaian.py backend/app/services/insight.py backend/app/services/beranda.py tests/integrasi/test_repositories.py tests/unit/test_services_analitik.py
```

## Ringkasan

| | |
|---|---|
| Prioritas | P1 |
| Perkiraan | sekitar sehari |
| Risiko ubahan | sedang |
| Bergantung pada | tidak ada |
| Cabang | `fix/seri-teramati` |
| Pesan commit | `Pisahkan seri tampilan beranda dari seri teramati analitik` |

## Mengapa ini penting

`repo_nilai.seri()` adalah seri **tampilan**: menyalin realisasi terdekat ke setiap tahun kosong di `range(2021, 2026)` dan menstempel `status_verifikasi=DISETUJUI` di memori (`satuan_catatan="Menggunakan nilai terdekat tahun …"`). Perilaku itu disengaja dan diuji di `tests/integrasi/test_repositories.py` sekitar 187–198.

`analitik.seri_realisasi`, `capaian.muatan` / `detail`, dan `insight._seri` semua memakai `seri()` dan mengabaikan `satuan_catatan`. Satu tahun teramati menjadi lima titik “disetujui” yang identik: perubahan YoY 0, `n` korelasi menggembung, grafik tren datar.

Kartu beranda harus **tetap** memakai isian celah (mereka menampilkan `keterangan`).

## Keadaan sekarang

- `backend/app/repositories/nilai.py` 123–167 — `seri()`: muat semua periode, ambil periode terakhir per `(tahun, jenis)`, lalu isi 2021–2025.
- `backend/app/services/analitik.py` 115–121:

```python
def seri_realisasi(session: Session, id_indikator: str) -> list[tuple[int, float]]:
    return [
        (baris.tahun, float(baris.nilai))
        for baris in repo_nilai.seri(session, id_indikator, KODE_PROVINSI, JenisNilai.REALISASI)
        if baris.nilai is not None
    ]
```

- `backend/app/services/capaian.py` 235 dan 297 — `muatan()` dan `detail()` memakai `repo_nilai.seri(...)`.
- `backend/app/services/insight.py` 70–86 — `_seri` mengiterasi `repo_nilai.seri(..., REALISASI)` untuk `growth`.
- `backend/app/services/beranda.py` 41 dan 76 — `_kartu_makro` / `_kartu_visi` memakai `seri()` **sengaja** (jangan diganti).
- Pemanggil `seri()` lain yang **sengaja di luar cakupan** plan ini: `ekspor.py` sekitar 230, `explorer.py` sekitar 75, `services/indikator.py` `detail()` sekitar 85. Jangan dialihkan di PR ini.
- Benih kontrak (`tests/api/conftest.py`) sudah punya realisasi 2021–2025 untuk ISV-001/002/005/IUP-001, jadi `test_analitik` kemungkinan `n >= 4` tetap. Tetap perlu tes **jarang** (satu tahun) agar perbaikan terkunci.

Komentar baru menjelaskan *mengapa* ada dua fungsi. Jangan taruh SQL di service.

## Cakupan

**Boleh diubah:**
- `backend/app/repositories/nilai.py` — ekstrak `seri_teramati()` (periode terbaru menang, **tanpa** isi 2021–2025). `seri()` memanggilnya lalu mengisi celah.
- `backend/app/services/analitik.py` — `seri_realisasi` membaca `seri_teramati`.
- `backend/app/services/capaian.py` — `muatan` dan `detail` membaca `seri_teramati`.
- `backend/app/services/insight.py` — `_seri` membaca `seri_teramati`.
- `tests/integrasi/test_repositories.py` — tes seri jarang.

**Jangan diubah:**
- Rentang isian 2021–2025.
- Batch query N+1.
- Kartu/peta insight yang memakai `ambil` / `terakhir_terisi` (itu plan 005).
- Komponen grafik frontend.
- Pemanggil `seri()` di `beranda.py`, `ekspor.py`, `explorer.py`, `services/indikator.py`.
- Seed / CRUD admin / unggah Excel (sudah di `main`).

## Langkah

### 1. Pecah fungsi repository, perilaku `seri()` tetap

Di `backend/app/repositories/nilai.py`:

```python
def seri_teramati(
    session: Session,
    id_indikator: str,
    wilayah_kode: str,
    jenis: str | None = None,
) -> list[NilaiIndikator]:
    """Rilis disetujui apa adanya: periode terbaru menang, tanpa mengisi tahun kosong."""
    stmt = _lingkup(select(NilaiIndikator), id_indikator, wilayah_kode, jenis, tahunan=False).order_by(
        NilaiIndikator.tahun, NilaiIndikator.jenis, NilaiIndikator.periode.asc().nullsfirst()
    )
    semua = list(session.scalars(stmt))
    terpilih = {(baris.tahun, baris.jenis): baris for baris in semua}
    return [terpilih[kunci] for kunci in sorted(terpilih)]
```

`seri()` membangun dict dari hasil `seri_teramati`, lalu menjalankan **loop isian yang sama** seperti sekarang (realisasi 2021–2025 + baris sintetis + `satuan_catatan`). Jangan ubah `test_seri_tampilan_mengisi_tahun_kosong_dengan_nilai_terdekat`.

Tambah `test_seri_teramati_tidak_mengisi_tahun_kosong` di samping tes itu: sisip hanya 2023=8.5 (pakai `_sisip_nilai` / `indikator_uji` yang sudah ada); tahun `seri_teramati` == `[2023]`; tahun `seri` tetap `2021..2025`.

**Cek:**

```text
python -m pytest tests/integrasi/test_repositories.py -q
```

Semua lulus.

### 2. Alihkan analitik / capaian / insight

- `analitik.seri_realisasi`: `repo_nilai.seri_teramati(..., JenisNilai.REALISASI)`.
- `capaian.muatan` dan `capaian.detail`: ganti `repo_nilai.seri` → `seri_teramati`.
- `insight._seri`: sama.

Biarkan `_kartu_makro` / `_kartu_visi` di beranda pada `seri()`.

Tambah `test_analitik_tidak_memakai_isian_celah` di `tests/integrasi/test_repositories.py`: satu tahun realisasi → `from backend.app.services.analitik import seri_realisasi` panjangnya 1 (bukan 5).

**Cek:**

```text
python -m pytest tests/integrasi/test_repositories.py tests/unit/test_services_analitik.py tests/unit/test_services_capaian.py tests/api/test_kontrak.py -q
```

Semua lulus.

Jika `test_analitik` korelasi `n` pada benih kontrak turun di bawah 4, **berhenti dan tanya** — jangan longgarkan tes disclaimer `n < 4`. Benih punya 2021–2025 jadi seharusnya tidak terjadi.

### 3. Lint

```text
ruff check backend/app/repositories/nilai.py backend/app/services/analitik.py backend/app/services/capaian.py backend/app/services/insight.py
mypy backend/app/repositories/nilai.py backend/app/services/analitik.py backend/app/services/capaian.py backend/app/services/insight.py
```

## Selesai bila semua ini benar

- [ ] Di `analitik.py`, `capaian.py`, `insight.py` tidak ada `repo_nilai.seri(` — hanya `seri_teramati`
- [ ] `beranda.py` masih memanggil `repo_nilai.seri(`
- [ ] `test_seri_tampilan_mengisi_tahun_kosong_dengan_nilai_terdekat` lulus
- [ ] Tes seri jarang lulus
- [ ] `python -m pytest tests/api/test_kontrak.py -q` kode keluar 0
- [ ] Baris 003 di `plans/improve-29-08-2026/README.md` menjadi `DONE`

Cara cek pemanggilan:

```text
rg "repo_nilai\\.seri\\(" backend/app/services/analitik.py backend/app/services/capaian.py backend/app/services/insight.py
rg "repo_nilai\\.seri\\(" backend/app/services/beranda.py
```

## Berhenti dan tanya

- Isian `seri()` sudah dihapus orang lain.
- `n` korelasi pada benih kontrak < 4.
- Kartu beranda kehilangan isian celah (beranda ikut dialihkan).
- Array `tren` capaian memendek untuk indikator jarang — itu **disengaja**, jangan berhenti karena itu.

## Catatan untuk peninjau

Plan 005 akan menambah `nilai_tampil` untuk peta; harus memakai baris teramati, bukan isian. Pastikan `keterangan` beranda masih “Menggunakan nilai terdekat tahun …”.
