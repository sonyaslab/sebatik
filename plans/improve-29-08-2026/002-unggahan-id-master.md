# 002 — DITOLAK: unggahan ID master sudah ditangani jalur Excel baru

Baca `plans/improve-29-08-2026/README.md` dan `AGENTS.md` sebelum mulai.

**Status:** `DITOLAK` — jangan dikerjakan. Temuan asli (unggahan massal `ISV-01` vs master `ISV-001`, lalu `terapkan()` tetap `DISETUJUI` dengan 0 baris) **sudah tidak berlaku** di `4a7939f`.

**Ditulis terhadap (awal):** `8b3ae9a`.
**Diperiksa ulang terhadap:** `4a7939f` (29 Agustus 2026).

## Mengapa ditolak

Antara `8b3ae9a` dan `4a7939f`, unggahan admin **bukan lagi** `src.etl.pipeline.run` + SQLite `.stage.db`. Jalur sekarang:

1. Gerbang hanya menerima `.xlsx` (`backend/app/routers/unggahan.py`).
2. `transformasi_workbook_excel` di `src/etl/database.py` membaca kolom `ID Indikator` dengan pola `^(ISV|IUP)-\d{3}$` (`POLA_ID`, baris 24).
3. Sheet nilai digabung lewat `(Kategori, Kode Indikator)`, bukan lewat ID — lihat docstring `transformasi_sumber_database` sekitar baris 65–77 (commit `2e83fe0`).
4. `validasi_dataset` (sekitar 206–223) menolak dataset yang tidak berisi **tepat 86** ID unik bermotif `ISV-001` / `IUP-001`. ID dua digit `ISV-01` tidak lolos pola, jadi pratinjau 422 (`BerkasTidakValid`) — bukan persetujuan senyap.
5. Tes `tests/api/test_unggahan.py` membangun workbook dengan `_id_uji` = `ISV-{n:03d}` / `IUP-{n:03d}`.

Cuplikan pengaman yang sekarang menggantikan skip senyap:

```python
# src/etl/database.py sekitar 222-223
if any(not isinstance(iid, str) or not POLA_ID.fullmatch(iid) for iid in ids):
    raise DatasetTidakValid("Semua ID indikator wajib memakai pola ISV-001/IUP-001")
```

`terapkan()` (`backend/app/services/unggahan.py` sekitar 171–236) memuat lewat `muat_dataset`, melindungi nilai `usulan_id` (`nilai_konflik`), lalu men-set `DISETUJUI`. Ia **tidak** lagi melewati ID tidak dikenal dengan `continue`.

Skema `DiffUnggahan` sekarang: `indikator_baru`, `indikator_hilang`, `nilai_berubah`, `nilai_konflik`, `ringkasan`. Field `id_tidak_dikenal` **tidak** perlu ditambahkan — ID salah gagal di validasi, bukan di diff.

## Yang jangan dilakukan

Jangan mengikuti draf lama plan ini (tes SQLite `.stage.db`, `_baca_staging`, `if id_indikator not in dikenal: continue`). Kode itu **sudah tidak ada**. Menghidupkannya akan menabrak jalur Excel yang baru.

Jangan mengubah `src/etl/common.py` `indicator_id()` (`ISV-01`). Fungsi itu masih dipakai pipeline ETL workbook lama (`src/etl/extract/`), **bukan** gerbang unggah admin. Pemetaan `ISV-01` → `ISV-001` otomatis tetap di luar cakupan (keputusan desain lama).

Jangan mengunci `terapkan` agar gagal bila `nilai_dimuat == 0`: unggahan dengan sheet nilai kosong/parsial **sengaja sah** (`validasi_dataset` baris 217–219). Semua nilai bisa terlindungi konflik verifikasi; status tetap `DISETUJUI` dengan `nilai_dilindungi` di ringkasan.

## Sisa yang terkait (bukan pekerjaan 002)

- Seed 86 indikator + CRUD admin sudah di `main` (`backend/app/cli.py` `seed-indikator`, `GET/POST /api/v1/admin/indikator`, `IndikatorManager.jsx`). Jangan diimplementasikan ulang.
- `indicator_id()` format `:02d` di ETL lama tetap utang terpisah bila seseorang masih menjalankan `python -m src.etl.pipeline` ke basis hidup. Bukan gerbang unggah.

Tidak ada langkah eksekusi. Ubah status di README batch hanya jika belum `DITOLAK`.
