# SEBATIK

Dasbor Pemantauan Ketersediaan dan Capaian Data Indikator ISV-IUP untuk BPS Provinsi Kalimantan Utara.

## Menjalankan aplikasi

Persyaratan: Python 3.11+ dan Node.js 20+. `pnpm` bersifat opsional; skrip otomatis memakai `npm` jika pnpm tidak tersedia.

```powershell
.\pasang-sebatik.ps1
.\jalankan-sebatik.ps1
```

Buka `http://localhost:8000`. Dokumentasi API tersedia di `http://localhost:8000/api/docs`. Hentikan dengan `Ctrl+C`.

`pasang-sebatik.ps1` menjalankan migrasi skema lalu membuat akun awal dan
**menampilkan sandinya satu kali**. Catat sandi tersebut; ia dibuat acak dan
tidak dapat dilihat lagi. Semua akun wajib mengganti sandi saat login pertama.

Untuk pengembangan frontend, jalankan `pnpm dev` di folder `frontend`; permintaan `/api` akan diteruskan ke FastAPI pada port 8000.

## Basis data

Skema dikelola Alembic. Tidak ada migrasi yang berjalan otomatis saat aplikasi dimulai.

```powershell
# Terapkan skema terbaru
python -m alembic -c backend/alembic.ini upgrade head

# Buat wilayah dan akun awal (idempoten; sandi akun lama tidak diubah)
python -m backend.app.cli seed --tampilkan-sandi

# Ringkasan kesiapan basis data
python -m backend.app.cli periksa
```

Bawaannya SQLite untuk pemasangan tunggal. Untuk PostgreSQL, setel
`SEBATIK_DATABASE_URL` di `.env`, lalu `docker compose up -d`. Compose sudah
memuat layanan PostgreSQL, langkah migrasi tersendiri, dan `pg_dump` harian
dengan retensi 30 berkas.

Memindahkan data dari pemasangan SQLite lama:

```powershell
python scripts/migrasi_ke_skema_target.py --periksa
python scripts/migrasi_ke_skema_target.py --jalankan
```

Skrip berjalan dalam satu transaksi dan membatalkan seluruh pemindahan bila
verifikasi jumlah baris gagal. Berkas sumber dibuka baca-saja dan tidak disentuh.

## Tata kelola data

Backend menggunakan alur `OPERATOR -> MENUNGGU_VERIFIKASI -> VERIFIKATOR -> DISETUJUI/DITOLAK`.
Operator hanya dapat mengirim data wilayahnya dan wajib mengunggah bukti dukung. Nilai per wilayah
baru tersedia untuk dashboard setelah disetujui; penolakan tidak mengubah angka publik. Admin
mengelola akun, status akses, wilayah, unggahan massal, dan audit.

Satu keputusan verifikasi menulis tepat satu baris `nilai_indikator` dalam satu transaksi.

Wilayah mencakup Provinsi Kalimantan Utara, Bulungan, Malinau, Nunukan, Tana Tidung, dan
Tarakan. Perintah seed menyiapkan dua akun operator per wilayah dengan pola `operator.<kode>.<1|2>`.

## Memperbarui data

Produksi tidak membaca Excel atau PDF secara langsung. Sumber yang telah
diklasifikasikan ditransformasi menjadi dataset JSON terstandar berversi, melewati
gerbang validasi, lalu dimuat ke PostgreSQL dalam satu transaksi.

```powershell
# Zona transformasi — tidak mengakses database produksi
python -m scripts.kelola_database transformasi `
  data/raw/basis_data_indikator_isv_iup_kaltara.json `
  data/processed/sebatik-database.json

# Gerbang mutu — wajib lulus sebelum persetujuan
python -m scripts.kelola_database validasi data/processed/sebatik-database.json

# Bootstrap/cutover langsung ke SEBATIK_DATABASE_URL
python -m scripts.kelola_database muat data/processed/sebatik-database.json
```

Untuk operasi rutin, admin mengunggah dataset database `.json`, memeriksa diff, lalu
menyetujuinya. Dataset mewajibkan tepat 86 ID master tiga digit, manifest jumlah
baris, integritas referensial, dan checksum SHA-256. Excel/PDF hanya boleh
dipakai oleh proses hulu untuk menghasilkan JSON sumber terklasifikasi.

Prosedur lengkap pengembangan, pull request, deployment, backup, pemuatan
PostgreSQL, verifikasi, dan rollback tersedia di
`docs/11-prosedur-etl-database.md`.

## Pengujian

```powershell
python -m pytest
ruff check .
mypy backend src

Set-Location frontend
pnpm lint
pnpm test
pnpm build
```

Tes kontrak API berjalan di atas data uji sendiri, jadi tidak memerlukan berkas
di `data/`. Tiga tes yang memang menguji data sungguhan (ETL dan regresi isi
beranda) melewatkan dirinya sendiri bila `data/` tidak tersedia.

## Catatan data

Isi `data/raw/` dan `data/processed/` **tidak** disertakan di repositori:
ukurannya besar, berubah setiap kali aplikasi berjalan, dan sebagian memuat data
pribadi. Salin dari berbagi pakai kantor sebelum menjalankan ETL.

Data PIC perorangan tersimpan di tabel privat `penugasan_pic` dan tidak tersedia melalui endpoint publik.
