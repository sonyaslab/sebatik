# Rencana perbaikan SEBATIK — 29 Agustus 2026

| | |
|---|---|
| Folder | `plans/improve-29-08-2026/` |
| Tanggal pembuatan | 29 Agustus 2026 |
| Commit acuan | `8b3ae9a` |
| Asal | satu pemanggilan audit `/improve` |

Dokumen ini untuk **developer** (manusia atau asisten kode di harness mana pun: Grok, Claude Code, OpenCode, Cursor, dll.). Tidak perlu skill, plugin, atau alur kerja khusus. Baca `AGENTS.md` di akar repositori, lalu kerjakan satu berkas plan di **folder ini**.

**Bukan bagian dari pekerjaan ini:** seed 86 indikator dan CRUD admin indikator. Itu sudah ada di `docs/superpowers/plans/2026-08-27-seed-indikator.md` dan `docs/superpowers/plans/2026-08-27-admin-manajemen-indikator.md` — jangan dicampur ke PR ini.

## Cara memakai

1. Baca `AGENTS.md` (arsitektur, konvensi, perintah tes).
2. Pilih **satu** baris TODO di tabel bawah. Kerjakan sampai selesai sebelum mengambil plan lain, kecuali 004 yang boleh paralel dengan 001/002.
3. Buat cabang dari `main` dengan nama yang disarankan di dalam berkas plan.
4. Ikuti langkah berurutan. Setiap langkah punya perintah cek dan hasil yang diharapkan.
5. Tulis tes yang **gagal** dulu, baru ubah kode produksi.
6. Komentar dan pesan commit berbahasa Indonesia.
7. Jangan push atau buka PR kecuali diminta.
8. Setelah selesai, ubah kolom Status di tabel ini menjadi `DONE`.

Kalau kode di lokasi yang dikutip plan sudah berbeda dari cuplikan (file berubah sejak `8b3ae9a`), **berhenti dan tanya** — jangan menerka.

## Urutan dan status

| Plan | Judul | Perkiraan | Bergantung | Status |
|------|-------|-----------|------------|--------|
| [001](001-usulan-periode-kosong.md) | Usulan tahunan dengan periode formulir kosong | beberapa jam | — | TODO |
| [002](002-unggahan-id-master.md) | Tolak unggahan massal tanpa irisan ID master | sekitar sehari | — | TODO |
| [003](003-seri-teramati.md) | Pisahkan seri tampilan beranda dari seri teramati | sekitar sehari | — | TODO |
| [004](004-wajib-ganti-password.md) | Tegakkan ganti sandi awal + sandi lama | beberapa jam | — | TODO |
| [005](005-katalog-publik-dan-periode.md) | Katalog publik hanya DISETUJUI; insight/peta memakai periode | beberapa jam | 003 | TODO |

Status: `TODO` | `SEDANG DIKERJAKAN` | `DONE` | `TERBENGKALAI (alasan satu baris)`

- 004 tidak bergantung pada yang lain; boleh dikerjakan bersamaan dengan 001 atau 002.
- 005 menyentuh `insight.py` / `capaian.py` yang sama dengan 003 — kerjakan setelah 003 selesai.
- Jangan campur 001/002 dengan pekerjaan seed-indikator.

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

Tes kontrak API memakai benih di `tests/api/conftest.py`, tidak butuh folder `data/`.

## Yang sengaja tidak dikerjakan di sini

- Admin tidak boleh memverifikasi usulan — memang aturan; tes `test_admin_tidak_boleh_memutuskan_usulan`.
- 63/86 indikator tanpa `arah_baik` — kondisi data, bukan bug kode.
- Token akses di `localStorage` — keputusan Opsi A; pindah ke cookie httpOnly adalah tindak lanjut terpisah.
- Pembatas laju login di memori proses — cukup untuk satu instans, tercatat di kode.
- Query N+1 di beranda (~86 indikator) — N kecil; ditinjau lagi jika seri kabupaten/kota masuk.
- SSO dan seri kabupaten/kota lengkap — keterbatasan produk (`docs/keterbatasan.md`).
- Katalog indikator kosong di Coolify — sudah direncanakan di plan seed-indikator.
