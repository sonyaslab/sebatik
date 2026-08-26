# Desain: Auto-seed Indikator + Manajemen Indikator via Admin

Tanggal: 2026-08-26

## Latar belakang

Deploy produksi (Coolify, via Dockerfile) sudah jalan tapi tabel `indikator`
kosong: `docker-entrypoint.sh` cuma menjalankan `alembic upgrade head` (bikin
skema) lalu langsung start server. Tidak ada langkah yang mengisi 86 baris
indikator ISV/IUP, sehingga operator tidak bisa mengirim nilai realisasi
(foreign key `nilai_indikator.id_indikator` tidak punya baris induk).

Populasi indikator saat ini cuma bisa lewat dua jalur manual:
1. ETL penuh (`src/etl/pipeline.py`) dari Excel raw ke staging, lalu admin
   approve lewat panel unggahan massal.
2. Migrasi dari instalasi SQLite lama (`scripts/migrasi_ke_skema_target.py`).

Keduanya butuh langkah manual eksplisit setiap kali server baru dipasang.
Dokumen ini merancang dua hal:

- **Bagian A** — mekanisme auto-seed yang mengisi indikator (+ metadata +
  nilai baseline provinsi) otomatis saat deploy pertama, tapi tidak
  mengulang saat redeploy.
- **Bagian B** — halaman admin baru untuk manajemen penuh (create/read/
  update/delete) daftar indikator dan metadatanya, menggantikan kebutuhan
  edit manual lewat script/DB langsung.

## Klarifikasi model data (tidak ada tabel baru)

Tiga tabel yang sudah ada di `backend/app/models/indikator.py` sudah cukup
dan tidak diubah strukturnya:

| Tabel | Peran | Contoh kolom relevan |
|---|---|---|
| `indikator` | Dimensi/identitas indikator (86 baris) | `id_indikator`, `kategori`, `kelompok`, `kode_indikator`, `nama_indikator`, `is_proxy`/`nama_proxy`, `opd_pengampu`, `status_ketersediaan`, `periode_data`, `arah_pembangunan`/`arah_ie` |
| `metadata_indikator` | Kartu definisi, FK 1:1 ke `indikator` | `definisi`, `rumus_mentah`, `interpretasi`, `sumber_data`, `frekuensi`, `status_metadata` |
| `nilai_indikator` | Fact table nilai realisasi/target, **satu tabel untuk semua wilayah & periode** | `id_indikator` (FK), `wilayah_kode` (FK, wajib), `tahun`, `jenis` (realisasi/target), `periode` (nullable), `nilai`/`nilai_teks`, `usulan_id` (FK, nullable), `status_verifikasi` |

Sempat dipertimbangkan bikin tabel baru "CapaianIndikator" khusus nilai
realisasi/target, tapi ditolak: `nilai_indikator` sudah persis itu, plus tiga
hal yang wajib ada dan tidak boleh disederhanakan:

- `wilayah_kode` — nilai dipecah per wilayah (provinsi + 5 kab/kota), bukan
  satu baris global per (indikator, tahun, jenis).
- `usulan_id` + `status_verifikasi` — kait ke seluruh alur tata kelola
  operator→verifikator yang sudah dibangun. Tabel terpisah akan memecah
  logic verifikasi jadi dua tempat.
- `periode` — sebagian indikator dilaporkan semesteran.

Baris hasil seed (bukan dari operator) ditulis dengan `usulan_id = NULL`,
`wilayah_kode = '65'` (provinsi), `status_verifikasi = DISETUJUI` (default
model) — sudah sesuai docstring model yang ada ("NULL bila berasal dari
basis data master/ETL").

## Bagian A — Auto-seed indikator, metadata, dan nilai baseline

### Sumber data

`data/raw/BASIS_DATA_INDIKATOR_ISV-IUP_KALTARA.xlsx`, dua sheet:

- **`Basis Data Indikator`** — 86 baris (dicek: tepat 86 baris berisi ID,
  cocok `ekspektasi.jumlah_indikator` di `workbook.yaml`). Sumber untuk
  `indikator` + `metadata_indikator`.
- **`Data Target-Realisasi`** — 660 baris bersih (dicek: tidak ada duplikat
  kunci `(id_indikator, tahun, jenis)`), format tidy: satu baris per
  indikator×tahun×jenis. Sumber untuk `nilai_indikator` (wilayah `65`).

File ini **beda skema** dari alur ETL lama (`src/etl/config/workbook.yaml`
yang mengharap sheet `"form provinsi"`) — jangan reuse `baca_master()`.
Mapping dibuat baru, khusus dua sheet ini.

### Mapping kolom `Basis Data Indikator` → model

| Kolom Excel | Kolom model | Catatan |
|---|---|---|
| ID Indikator | `indikator.id_indikator` | PK langsung, format `ISV-001`/`IUP-001` (3 digit, beda dari format lama `indicator_id()` yang 2 digit — **jangan** pakai fungsi itu) |
| Kategori | `indikator.kategori` | |
| Kelompok / Pilar | `indikator.kelompok` | Sama makna utk ISV & IUP (dicek silang lewat `tests/api/conftest.py`: IUP-001 → "Transformasi Sosial" cocok fixture yang sudah ada) |
| Arah Pembangunan | `indikator.arah_pembangunan` bila `kategori == ISV`; `indikator.arah_ie` bila `kategori == IUP` | Satu kolom Excel, beda arti per kategori — dicek: baris IUP-001 isinya "IE1 - Kesehatan untuk Semua" (format `arah_ie`, bukan `arah_pembangunan`) |
| Kode Indikator | `indikator.kode_indikator` | |
| Nama Indikator (RPJPD Provinsi / dipakai Kaltara) | `indikator.nama_indikator` | |
| Indikator Proxy? + kolom keterangan RPJMD | `indikator.is_proxy`, `indikator.nama_proxy` | Reuse `src/etl/transform/proxy.py:ekstrak_proxy()` yang sudah ada, jangan tulis ulang |
| Definisi (RPJPD Provinsi) | `metadata_indikator.definisi` | |
| Rumus Perhitungan (RPJPD Provinsi) | `metadata_indikator.rumus_mentah` | Teks mentah (ada artefak simbol OCR), bukan `rumus`/`rumus_latex` |
| Interpretasi (RPJPD Provinsi) | `metadata_indikator.interpretasi` | |
| Sumber Data (RPJPD Provinsi) | `indikator.sumber_data` **dan** `metadata_indikator.sumber_data` | Kolom sama ada di kedua tabel, tulis nilai sama ke keduanya |
| Frekuensi (RPJPD Provinsi) | `indikator.frekuensi` **dan** `metadata_indikator.frekuensi` | idem |
| Status Metadata | `indikator.status_metadata` **dan** `metadata_indikator.status_metadata` | idem |
| Perangkat Daerah Pengampu (Kaltara) | `indikator.opd_pengampu` | |
| Ketersediaan Data | `indikator.status_ketersediaan` | |
| Periode Data | `indikator.periode_data` | |
| Tahun Data Terakhir | `indikator.tahun_terakhir` | Parse ke int |
| Catatan Kualitas Data + Keterangan (Rakor Kaltara) + Keterangan RPJMD / Catatan Kaltara | `indikator.catatan_teknis` | **Gabung ketiganya** jadi satu string multi-baris, tiap baris diberi prefiks label asal, mis. `[Catatan Kualitas Data] ...`, `[Rakor Kaltara] ...`, `[RPJMD] ...` — hanya baris yang tidak kosong yang disertakan |
| Realisasi 2021..2025, Target 2025..2045 | **tidak dipakai** | Redundan dengan sheet `Data Target-Realisasi` yang lebih rapi; dipakai sheet kedua sebagai sumber nilai |
| Jumlah Tahun Realisasi Terisi, Kelengkapan Realisasi (%), Status Ketersediaan Realisasi, Selisih Realisasi 2025–Target 2025 | **tidak disimpan** | Statistik turunan, bisa dihitung ulang dari `nilai_indikator`, bukan kolom model |
| (tidak ada di sheet) | `kode_sdgs`, `link_metadata`, `link_publikasi`, `link_data`, `status_rpjmd`, `arah_baik`, `arah_baik_terverifikasi`, `tim_pjk`, `kl_pengampu`, `penghasil`, `indikator_induk`, `kelompok_makro`, `misi_agenda`, `sumber_master`, dan seluruh kolom `metadata_indikator` lain (`rumus`, `rumus_latex`, `halaman_sumber`, `perlu_verifikasi_manual`, `sumber_metadata`, `nama_di_buku1`) | **NULL** — tidak ada di sumber ini, diisi belakangan lewat admin CRUD (Bagian B) atau endpoint `/arah-baik/{id}` yang sudah ada |

`nomor` (kolom `indikator.nomor`, Integer) diturunkan dari suffix numerik
`id_indikator` (mis. `ISV-001` → `1`), bukan dari kolom "Kode Indikator" yang
nilainya kadang beda representasi.

### Mapping `Data Target-Realisasi` → `nilai_indikator`

| Kolom Excel | Kolom model |
|---|---|
| ID Indikator | `id_indikator` (FK) |
| Jenis Nilai (`"Realisasi"`/`"Target"`) | `jenis` (`JenisNilai.REALISASI`/`JenisNilai.TARGET`, lowercase) |
| Tahun | `tahun` |
| Nilai (Angka) | `nilai` |
| Nilai (Teks Asli) | `nilai_teks` |
| Satuan/Catatan | `satuan_catatan` |
| — | `wilayah_kode = '65'` (provinsi, tetap) |
| — | `periode = NULL` (tahunan) |
| — | `usulan_id = NULL`, `status_verifikasi = DISETUJUI` (default model) |
| — | `sumber = "seed_awal:BASIS_DATA_INDIKATOR_ISV-IUP_KALTARA.xlsx"` (jejak provenance) |

### Mekanisme

1. **Skrip ekspor** baru: `scripts/ekspor_seed_indikator.py`. Baca dua sheet
   di atas dari `data/raw/BASIS_DATA_INDIKATOR_ISV-IUP_KALTARA.xlsx`
   memakai mapping di atas, hasilnya ditulis ke
   `backend/alembic/data/indikator_seed.json` (struktur:
   `{"indikator": [...], "metadata_indikator": [...], "nilai_indikator": [...]}`).
   File JSON ini **di-commit ke git** — bukan Excel-nya (tetap ikuti aturan
   `data/raw/` tidak ter-commit).
2. **Migrasi Alembic baru** `backend/alembic/versions/0004_seed_indikator.py`,
   pola identik `0002_seed_wilayah.py`: baca `indikator_seed.json` saat
   `upgrade()`, `op.bulk_insert()` ke tiga tabel berurutan (`indikator` →
   `metadata_indikator` → `nilai_indikator`, sesuai urutan FK).
   `downgrade()` hapus baris-baris itu by `id_indikator` (nilai dan metadata
   ikut terhapus lewat filter FK yang sama).
3. **Tidak ada perubahan** di `docker-entrypoint.sh` atau `cli.py` — migrasi
   ini otomatis kebawa oleh `alembic upgrade head` yang sudah jalan di
   entrypoint. Idempoten native: migrasi tercatat di `alembic_version`,
   sekali jalan per instalasi, redeploy = no-op.

### File yang dibuat/diubah (Bagian A)

- `scripts/ekspor_seed_indikator.py` (baru)
- `backend/alembic/data/indikator_seed.json` (baru, di-generate lalu commit)
- `backend/alembic/versions/0004_seed_indikator.py` (baru)

## Bagian B — Admin CRUD manajemen indikator

### Endpoint

Semua di `backend/app/routers/admin.py`, prefix `/api/v1/admin/indikator`,
dilindungi `wajib_peran(Peran.ADMIN)` (pola sama seperti endpoint admin lain
di berkas ini).

| Method | Path | Fungsi |
|---|---|---|
| GET | `/admin/indikator` | List penuh — semua kolom (bukan cuma `FIELD_PUBLIK`), reuse `repo_indikator.cari()` (filter q/kategori/kelompok/tim/status_metadata, sort, pagination sudah ada) |
| GET | `/admin/indikator/{id_indikator}` | Detail satu baris, `indikator` + `metadata_indikator` digabung, buat prefill form edit |
| POST | `/admin/indikator` | Buat baru: insert `indikator` + `metadata_indikator` (boleh kosong) dalam satu transaksi |
| PUT | `/admin/indikator/{id_indikator}` | Ganti field yang bisa diedit — **full-replace semantics** (semua field editable wajib dikirim ulang oleh form, bukan partial patch), supaya tidak ambigu `None` = "kosongkan" vs "tidak dikirim" |
| DELETE | `/admin/indikator/{id_indikator}` | Hapus `indikator` + `metadata_indikator` (cascade). **Ditolak 409** kalau `nilai_indikator` masih ada baris utk id itu |

### Validasi

- **Create**: `id_indikator` diisi manual admin lewat form, tapi divalidasi
  di service layer harus konsisten `f"{kategori}-{nomor:03d}"` (mis.
  kategori=`ISV`, nomor=`87` → wajib `"ISV-087"`). Tidak cocok → 422 lewat
  `Penolakan`. Duplikat PK → `IntegrityError` di-catch di router → 409
  (pola sama `buat_pengguna` di berkas yang sama).
- **Delete**: repo cek `EXISTS` di `nilai_indikator` utk `id_indikator`
  sebelum hapus; kalau ada → `Penolakan` 409, pesan jelas ("indikator masih
  punya histori nilai, tidak bisa dihapus").

### Field yang bisa diedit

Dari `indikator`: `kategori`\*, `nomor`\*, `kode_indikator`, `nama_indikator`\*,
`nama_asli`, `kelompok`, `arah_pembangunan`, `sasaran_visi`, `misi_agenda`,
`arah_ie`, `indikator_induk`, `kelompok_makro`, `satuan`, `penghasil`,
`kl_pengampu`, `opd_pengampu`, `tim_pjk`, `sumber_data`, `frekuensi`,
`status_ketersediaan`, `status_metadata`, `periode_data`, `tahun_terakhir`,
`is_proxy`, `nama_proxy`, `status_rpjmd`, `kode_sdgs`, `link_metadata`,
`link_publikasi`, `link_data`, `catatan_teknis` (\* = wajib).

Dari `metadata_indikator`: `definisi`, `interpretasi`, `sumber_data`,
`frekuensi`, `rumus`, `rumus_mentah`, `rumus_latex`, `halaman_sumber`,
`perlu_verifikasi_manual`, `sumber_metadata`, `nama_di_buku1`,
`status_metadata`.

**Tidak termasuk** (sengaja dikecualikan dari form ini):
- `arah_baik`, `arah_baik_terverifikasi` — tetap lewat endpoint khusus
  `PUT /api/v1/arah-baik/{id_indikator}` yang sudah ada. Tidak diduplikasi
  di sini supaya tidak ada dua jalur yang menulis field yang sama.
- `status_verifikasi` — tetap dikelola sistem, selalu `DISETUJUI` untuk
  data yang ditulis admin (admin adalah otoritas tertinggi tata kelola,
  konsisten dengan alur verifikasi nilai yang sudah ada).

### Audit

- **Create/Delete** → `LogAktivitas` (`aksi = "indikator_dibuat"` /
  `"indikator_dihapus"`, `objek_tipe = "indikator"`,
  `objek_id = id_indikator`). Untuk delete, `detail` menyimpan snapshot JSON
  baris yang dihapus (forensik, bisa dipulihkan manual kalau salah pencet).
- **Update** → `LogPerubahan` **per kolom yang nilainya berubah** (bandingkan
  lama vs baru sebelum commit), `sumber_perubahan = "edit_admin"` — pola
  identik `koreksi_arah_baik` yang sudah ada di
  `backend/app/services/indikator.py`.

### Frontend

- Komponen baru `frontend/src/components/admin/IndikatorManager.jsx`:
  tabel daftar indikator (search/filter/sort/pagination, reuse
  `api/endpoints.js` baru utk endpoint di atas), tombol "Tambah Indikator"
  buka form create, tombol edit per baris buka form yang sama terisi data.
  Form dibagi 3 seksi biar tidak jadi satu scroll raksasa: **Identitas &
  Klasifikasi**, **Kepemilikan & Ketersediaan**, **Metadata & Definisi**.
  Tombol hapus nonaktif (dengan tooltip) kalau `nilai_indikator` masih ada
  utk indikator itu (dicek dari respons GET detail, backend tetap jadi
  penjaga akhir lewat 409).
- Dipasang sebagai Panel baru di `frontend/src/pages/AdminPage.jsx` (halaman
  itu sendiri tetap tipis — cuma import & render komponen, tidak menampung
  logic tabel/form).

### File yang dibuat/diubah (Bagian B)

- `backend/app/schemas/indikator.py` — tambah schema request/response admin
  (mis. `AdminIndikatorDetailResponse`, `AdminDaftarIndikatorResponse`,
  `IndikatorDibuatResponse`).
- `backend/app/repositories/indikator.py` — tambah `buat()`, `perbarui()`,
  `hapus()`, `punya_nilai()`.
- `backend/app/services/indikator.py` — tambah `periksa_pembuatan()`,
  `buat_indikator()`, `perbarui_indikator()`, `periksa_penghapusan()`,
  `hapus_indikator()`, mengikuti pola `Penolakan` yang sudah ada.
- `backend/app/routers/admin.py` — tambah 5 endpoint di atas.
- `frontend/src/api/endpoints.js` — tambah fungsi pemanggil endpoint baru.
- `frontend/src/components/admin/IndikatorManager.jsx` (baru).
- `frontend/src/pages/AdminPage.jsx` — mount komponen baru.

## Pengujian

- Backend: `tests/unit/test_arsitektur.py` tetap harus lolos (router tanpa
  `select()`/loop/dict >5 kunci — logic penyusunan muatan admin list/detail
  masuk service, bukan router). `tests/api/test_kontrak.py` tidak berubah
  (endpoint publik tidak disentuh). Tes baru: kontrak CRUD admin (create
  sukses, id tidak konsisten → 422, duplikat → 409, delete diblokir kalau
  ada nilai, log audit tercatat).
- Migrasi: `alembic upgrade head` lalu `downgrade -1` terhadap PostgreSQL
  asli (CI sudah melakukan ini) harus bersih dua arah.
- Frontend: `pnpm test` utk `IndikatorManager.jsx`, `pnpm lint`, `pnpm build`.
- Manual: jalankan `scripts/ekspor_seed_indikator.py` dari Excel yang sudah
  ditaruh, cek `indikator_seed.json` masuk akal (86 indikator, 660 nilai),
  `alembic upgrade head` di DB kosong → cek 86 baris `indikator` + nilai
  provinsi ke-load, ulangi `alembic upgrade head` → no-op (revisi sudah
  diterapkan).

## Di luar cakupan

- Menu manajemen nilai realisasi/target per wilayah kabupaten/kota (itu
  tetap lewat alur usulan operator→verifikator yang sudah ada, tidak
  disentuh dokumen ini).
- Re-strukturisasi `indikator`/`metadata_indikator` jadi satu tabel gabungan
  — dipertimbangkan tapi ditolak (lihat "Klarifikasi model data"), perubahan
  itu terlalu besar dan berisiko untuk digabung dengan pekerjaan ini.
