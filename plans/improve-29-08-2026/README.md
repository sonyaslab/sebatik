# Rencana perbaikan SEBATIK — 29 Agustus 2026

| | |
|---|---|
| Folder | `plans/improve-29-08-2026/` |
| Tanggal pembuatan | 29 Agustus 2026 |
| Commit acuan awal | `8b3ae9a` |
| Disesuaikan terhadap | `4a7939f` (29 Agustus 2026) |
| Asal | satu pemanggilan audit `/improve` |

Dokumen ini untuk **developer** (manusia atau asisten kode di harness mana pun: Grok, Claude Code, OpenCode, Cursor, dll.). Tidak perlu skill, plugin, atau alur kerja khusus. Baca `AGENTS.md` di akar repositori, lalu kerjakan satu berkas plan di **folder ini**.

**Bukan bagian dari pekerjaan ini:** seed 86 indikator, CRUD admin indikator, dan unggah Excel admin. Ketiganya **sudah di `main`** (CLI `seed-indikator`, `GET/POST /api/v1/admin/indikator`, `IndikatorManager` / `UnggahExcelPanel`). Jangan diimplementasikan ulang. Plan lama di `docs/superpowers/plans/2026-08-27-*.md` adalah catatan sejarah.

## Rekonsiliasi 29 Agustus 2026

`origin/main` maju dari `8b3ae9a` ke `4a7939f` sebelum batch ini dieksekusi. Yang berubah dan dampaknya ke plan:

| Perubahan di `main` | Dampak |
|---|---|
| Seed CLI + `indikator_seed.json` | Katalog produksi bisa terisi. Bukan pekerjaan 001–005. |
| CRUD admin indikator | `daftar_admin` memakai `repo_indikator.cari()` yang sama dengan katalog publik. Plan 005 wajib parameter `hanya_terverifikasi`, bukan saring buta. |
| Unggah Excel `.xlsx` + validasi 86 ID `ISV-001` | Temuan 002 (skip `ISV-01` lalu `DISETUJUI`) **hilang**. Plan 002 `DITOLAK`. |
| `AdminPage` memasang `UnggahExcelPanel` + `IndikatorManager` | Plan 001 hanya form usulan. Plan 004 harus early-return sebelum `Shell` agar panel baru tidak terpasang saat bendera ganti sandi. |

Bug 001, 003, 004, 005 **masih ada** di `4a7939f`.

## Cara memakai

1. Baca `AGENTS.md` (arsitektur, konvensi, perintah tes).
2. Pilih **satu** baris TODO di tabel bawah. Kerjakan sampai selesai sebelum mengambil plan lain, kecuali 004 yang boleh paralel dengan 001.
3. Buat cabang dari `main` dengan nama yang disarankan di dalam berkas plan.
4. Ikuti langkah berurutan. Setiap langkah punya perintah cek dan hasil yang diharapkan.
5. Tulis tes yang **gagal** dulu, baru ubah kode produksi.
6. Komentar dan pesan commit berbahasa Indonesia.
7. Jangan push atau buka PR kecuali diminta.
8. Setelah selesai, ubah kolom Status di tabel ini menjadi `DONE`.

Kalau kode di lokasi yang dikutip plan sudah berbeda dari cuplikan (file berubah sejak `4a7939f`), **berhenti dan tanya** — jangan menerka.

## Urutan dan status

| Plan | Judul | Perkiraan | Bergantung | Status |
|------|-------|-----------|------------|--------|
| [001](001-usulan-periode-kosong.md) | Usulan tahunan dengan periode formulir kosong | beberapa jam | — | DONE |
| [002](002-unggahan-id-master.md) | Tolak unggahan massal tanpa irisan ID master | — | — | DITOLAK (diperbaiki independen) |
| [003](003-seri-teramati.md) | Pisahkan seri tampilan beranda dari seri teramati | sekitar sehari | — | DONE |
| [004](004-wajib-ganti-password.md) | Tegakkan ganti sandi awal + sandi lama | beberapa jam | — | DONE |
| [005](005-katalog-publik-dan-periode.md) | Katalog publik hanya DISETUJUI; insight/peta memakai periode | beberapa jam | 003 | DONE |

Status: `TODO` | `SEDANG DIKERJAKAN` | `DONE` | `TERBENGKALAI (alasan satu baris)` | `DITOLAK (alasan satu baris)`

### Catatan pelaksanaan 30 Agustus 2026

Keempat plan TODO dikerjakan dalam satu rangkaian di atas `0dc059d`, bukan dari
`main` — `main` masih tertinggal di belakang batch seed/CRUD/unggah Excel, jadi
mencabang dari sana akan kehilangan kode yang justru dirujuk plan.

- **001** — tes langkah 1 lulus tanpa ubahan produksi: FastAPI 0.141.1 yang
  terpasang mengikat `periode=""` menjadi `None` sendiri. Pin `fastapi>=0.115,<1`
  masih memuat versi yang menolaknya, jadi perbaikannya tetap diterapkan supaya
  perilakunya tidak bergantung versi yang kebetulan terpasang.
- **004** — `PESAN_PASSWORD_PENDEK` sebelumnya ditulis dua kali (`services/auth.py`
  dan `services/pengguna.py`) dan hanya menyebut batas minimum. Kini satu sumber
  `PESAN_PANJANG_PASSWORD` di `security.py`, di samping angka kebijakannya.
- **003** — `n` korelasi pada benih kontrak tetap 5 setelah peralihan ke
  `seri_teramati`, jadi tidak ada kondisi berhenti.
- Di luar plan: `tests/integrasi/test_service_indikator_admin.py` masih memanggil
  `periksa_konfirmasi_penghapusan` dengan dua argumen — sisa dari `505fc1a` yang
  sengaja mengubahnya menjadi bendera boolean tetapi melewatkan berkas tes ini.
  Disamakan supaya baseline hijau.

### Verifikasi 31 Agustus 2026

Seluruh rangkaian cek dijalankan ulang di atas hasil batch: `python -m pytest`
(539 lulus, cakupan 87%), `ruff check`, `ruff format --check`, `mypy backend src`,
serta `pnpm lint` / `pnpm test` / `pnpm build` di `frontend/`. Dua perbaikan di
luar isi plan supaya perintah cek di berkas ini benar-benar hijau:

- `backend/app/routers/admin.py` dan `tests/api/test_admin_indikator.py` punya
  akhiran baris campur sejak `505fc1a` (beberapa baris LF di berkas CRLF), jadi
  `ruff format --check` menolaknya. Dinormalkan; isinya tidak berubah.
- `plans/**` masuk daftar kecuali `[tool.ruff.format]` di `pyproject.toml`,
  sejajar dengan `docs/**`: berkas plan memuat cuplikan Python sebagai ilustrasi
  yang memang dipotong seperlunya.

- 002 **jangan dikerjakan**. Jalur unggah sekarang memvalidasi ID tiga digit.
- 004 tidak bergantung pada yang lain; boleh dikerjakan bersamaan dengan 001.
- 005 menyentuh `insight.py` / `capaian.py` yang sama dengan 003 — kerjakan setelah 003 selesai.
- Jangan campur 001 dengan pekerjaan seed/CRUD/unggah Excel.

## Konvensi yang wajib diikuti

Salinan ringkas dari `AGENTS.md`. Kalau bentrok, `AGENTS.md` yang menang.

- Komentar dan pesan commit berbahasa Indonesia. Nama fungsi backend baru berbahasa Indonesia.
- Lapisan: `routers → services → repositories → models`. Ditegakkan tes `tests/unit/test_arsitektur.py`.
  - Router: tanpa SQL, tanpa perulangan, dict respons paling banyak lima kunci.
  - Service: tidak mengimpor FastAPI; penolakan = `Penolakan(kode, pesan)` dari `backend/app/services/__init__.py`.
  - SQL mentah `text("...")` hanya di `repositories/`.
- Frontend: halaman memanggil `frontend/src/api/endpoints.js`, bukan `fetch` langsung.
- Enum domain dari `backend/app/models/enums.py` (`DISETUJUI`, `KODE_PROVINSI`, …), bukan string literal baru.
- Python baru: `from __future__ import annotations`.
- Jangan menambah dependensi.

## Perintah cek (dari akar repositori)

```text
python -m pytest
ruff check . ; ruff format --check . ; mypy backend src
cd frontend && pnpm lint && pnpm test && pnpm build
```

Tes kontrak API memakai benih di `tests/api/conftest.py` (5 indikator, termasuk `IUP-002` draf), tidak butuh folder `data/`. Seed produksi 86 baris tidak dipakai tes API.

## Yang sengaja tidak dikerjakan di sini

- Admin tidak boleh memverifikasi usulan — memang aturan; tes `test_admin_tidak_boleh_memutuskan_usulan`.
- 63/86 indikator tanpa `arah_baik` — kondisi data, bukan bug kode.
- Token akses di `localStorage` — keputusan Opsi A; pindah ke cookie httpOnly adalah tindak lanjut terpisah.
- Pembatas laju login di memori proses — cukup untuk satu instans, tercatat di kode.
- Query N+1 di beranda (~86 indikator) — N kecil; ditinjau lagi jika seri kabupaten/kota masuk.
- SSO dan seri kabupaten/kota lengkap — keterbatasan produk (`docs/keterbatasan.md`).
- Katalog indikator kosong di Coolify — ditangani seed yang sudah di `main`.
- Unggahan ID `ISV-01` vs master — ditangani validasi dataset Excel (plan 002 ditolak).
