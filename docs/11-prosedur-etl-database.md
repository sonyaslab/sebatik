# Prosedur ETL Database SEBATIK

Dokumen ini menjadi prosedur operasional transformasi dan pemuatan data master
SEBATIK ke PostgreSQL. Ada dua jalur resmi, dan keduanya melewati gerbang
validasi yang sama (`validasi_dataset`): manifest, pola ID, integritas
referensial, dan checksum SHA-256. PDF tetap berhenti di zona sumber.

- **Jalur CLI (rilis terkendali).** Dipakai deployment container dan CI.
  Berbasis JSON dataset yang ikut direview di pull request.
- **Jalur UI admin (pemutakhiran rutin).** Admin mengunggah `.xlsx` langsung
  dari halaman admin, memeriksa pratinjau perubahan, lalu menyetujuinya.
  Tidak butuh terminal.

## 1. Alur dan pemisahan tanggung jawab

Jalur CLI:

```text
Excel/PDF sumber
  -> klasifikasi dan pemeriksaan sumber
  -> JSON sumber terklasifikasi
  -> transformasi dataset database
  -> validasi manifest, ID, referensi, dan checksum
  -> review pull request
  -> deployment aplikasi
  -> backup PostgreSQL
  -> pemuatan satu transaksi
  -> verifikasi API dan dasbor
```

Jalur UI admin:

```text
Excel .xlsx
  -> unggah di halaman admin
  -> konversi src/etl/excel.py + validasi dataset yang sama
  -> pratinjau diff (indikator baru/hilang, nilai berubah, nilai dilindungi)
  -> persetujuan admin
  -> pemuatan satu transaksi
```

**Nilai dilindungi.** Nilai yang berasal dari alur usulan operator ->
verifikator (`nilai_indikator.usulan_id` terisi) tidak pernah ditimpa
unggahan massal. Baris seperti itu ditampilkan terpisah di pratinjau beserta
nomor usulannya, dan dilewati saat pemuatan.

**Kunci gabung dua sheet.** `Basis Data Indikator` dan `Data Target-Realisasi`
digabung lewat `(Kategori, Kode Indikator)`, bukan lewat kolom `ID Indikator`.
Penomoran IUP kedua sheet berbeda; menggabungkan lewat ID menempelkan
realisasi ke indikator yang salah tanpa galat apa pun.

| Peran | Tanggung jawab |
|---|---|
| Pengelola data | Memeriksa sumber dan menghasilkan JSON sumber terklasifikasi. |
| Pengembang | Menjalankan transformasi, tes, dan menyiapkan pull request. |
| Reviewer | Memeriksa diff kode, hasil tes, manifest, dan perubahan kontrak. |
| Operator produksi | Menjalankan backup, deployment, pemuatan, dan verifikasi. |

Pengembang tidak memuat database produksi dari komputer kerja. Operator
produksi tidak mengubah dataset setelah checksum disetujui.

## 2. Persiapan lingkungan pengembangan

Jalankan dari root repositori menggunakan PowerShell:

```powershell
python -m venv .venv-database
& .\.venv-database\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -c "import sqlalchemy, alembic; print('Dependensi siap')"
```

Jika kebijakan PowerShell menolak aktivasi, interpreter dapat dipanggil
langsung:

```powershell
& .\.venv-database\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## 3. Transformasi dataset database

```powershell
python -m scripts.kelola_database transformasi `
  data/raw/basis_data_indikator_isv_iup_kaltara.json `
  data/processed/sebatik-database.json
```

Hasil yang diharapkan:

```text
Dataset dibuat: data\processed\sebatik-database.json
manifest={'indikator': 86, 'metadata_indikator': 86, 'nilai_indikator': ...}
```

Kolom `dibuat_pada` boleh berubah setiap transformasi. `checksum_data` harus
tetap sama bila isi tabel tidak berubah.

## 4. Gerbang validasi dan pengujian

```powershell
python -m scripts.kelola_database validasi `
  data/processed/sebatik-database.json

python -m ruff check .
python -m mypy backend src
python -m pytest
```

Validasi menolak dataset bila:

- versi bukan `sebatik.database/v1`;
- master tidak berisi tepat 86 ID unik tiga digit;
- metadata atau nilai mengacu ke indikator yang tidak dikenal;
- nilai tahunan memiliki kunci ganda;
- jumlah pada manifest berbeda dari isi;
- checksum SHA-256 tidak sesuai.

Dataset di `data/` tidak dimasukkan ke Git. Distribusikan dataset ke operator
produksi lewat penyimpanan internal yang memiliki kontrol akses.

## 5. Branch, commit, dan pull request

Gunakan nama branch yang menjelaskan fungsi bisnis dan tidak memuat nama alat:

```powershell
git switch -c feature/etl-database-postgresql

git add README.md `
  docs/11-prosedur-etl-database.md `
  docs/refactoring/CATATAN-PELAKSANAAN.md `
  src/etl/database.py `
  scripts/kelola_database.py `
  backend/app/services/unggahan.py `
  backend/app/routers/unggahan.py `
  tests/etl/test_database.py

git diff --cached --check
git status --short
git commit -m "perbaiki proses ETL database PostgreSQL"
git push -u origin feature/etl-database-postgresql
```

Jangan masukkan `.env`, sandi, database SQLite, dataset hasil transformasi,
Excel, PDF, bukti dukung, atau arsip unggahan ke commit.

Buat pull request dari `feature/etl-database-postgresql` menuju branch produksi.
Deskripsi pull request minimal memuat:

1. alasan perubahan;
2. kontrak `sebatik.database/v1`;
3. manifest hasil transformasi;
4. hasil ruff, mypy, dan pytest;
5. prosedur deployment dan rollback;
6. konfirmasi tidak ada data/rahasia dalam commit.

Merge hanya dilakukan setelah CI dan review lulus.

## 6. Deployment aplikasi di server

Perintah berikut dijalankan operator pada server setelah pull request di-merge:

```bash
git fetch upstream
git switch main
git pull --ff-only upstream main

docker compose build migrasi sebatik
docker compose up -d db
docker compose run --rm migrasi
docker compose up -d sebatik backup
docker compose ps
```

Sesuaikan `main` bila branch produksi memakai nama lain. Jangan memuat dataset
sebelum container `migrasi` selesai dengan kode keluar nol.

## 7. Penyerahan dataset ke container

Salin `sebatik-database.json` ke direktori proyek server melalui kanal internal,
kemudian:

```bash
docker compose cp \
  data/processed/sebatik-database.json \
  sebatik:/app/data/processed/sebatik-database.json

docker compose exec sebatik \
  python -m scripts.kelola_database validasi \
  /app/data/processed/sebatik-database.json
```

Catat checksum yang tampil dalam berita acara atau tiket perubahan.

## 8. Backup dan pemuatan PostgreSQL

Buat backup tepat sebelum pemuatan:

```bash
docker compose exec backup sh -c \
  'pg_dump -h db -U sebatik -d sebatik -Fc -f /backup/sebatik-sebelum-etl.dump'
```

Muat dataset melalui container aplikasi agar `SEBATIK_DATABASE_URL` memakai
jaringan dan kredensial produksi yang sama dengan API:

```bash
docker compose exec sebatik \
  python -m scripts.kelola_database muat \
  /app/data/processed/sebatik-database.json
```

Loader menjalankan upsert dimensi, metadata, dan fakta dalam satu transaksi.
Kegagalan menyebabkan rollback; tidak ada kondisi terisi sebagian.

## 9. Verifikasi setelah pemuatan

```bash
curl --fail https://sebatik.kaltarastats.id/api/v1/health
curl --fail https://sebatik.kaltarastats.id/api/v1/indikator
curl --fail https://sebatik.kaltarastats.id/api/v1/beranda
docker compose logs --tail=100 sebatik
```

Kriteria penerimaan:

- health mengembalikan `status: ok`;
- daftar indikator mengembalikan `total: 86`;
- beranda memiliki `tahun_tersedia` yang tidak kosong;
- tidak ada galat 500 pada log;
- data tampil setelah hard refresh peramban;
- checksum dan waktu pemuatan tercatat.

## 10. Rollback

Jika validasi pascapemuatan gagal, hentikan penulisan baru lalu pulihkan backup:

```bash
docker compose exec db dropdb -U sebatik sebatik
docker compose exec db createdb -U sebatik sebatik
docker compose exec backup pg_restore \
  -h db -U sebatik -d sebatik \
  /backup/sebatik-sebelum-etl.dump
```

Setelah pemulihan, jalankan kembali pemeriksaan health, indikator, beranda, dan
log. Catat penyebab rollback sebelum percobaan pemuatan berikutnya.
