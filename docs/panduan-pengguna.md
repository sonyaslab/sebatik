# Panduan Pengguna SEBATIK

## 1. Memantau ketersediaan

Buka menu **Ketersediaan**. Kartu atas menunjukkan jumlah indikator, cakupan kabupaten/kota, metadata yang belum tersedia, dan penggunaan proxy. Klik sel pada matriks untuk menyaring tabel.

![Halaman ketersediaan](images/01-ketersediaan.png)

## 2. Melihat capaian

Buka **Capaian ISV-IUP**. Gunakan filter kategori, Tim PJK, dan status capaian. Klik kartu untuk membuka grafik realisasi-target, metadata, tata kelola, tabel nilai, serta unduhan indikator.

![Halaman capaian](images/02-capaian.png)

Status `BELUM ADA DATA` berarti realisasi/target sebanding belum tersedia; sistem tidak menampilkannya sebagai nol persen. Arah NAIK/TURUN masih dapat dikoreksi admin.

## 3. Menggunakan analitik

Buka **Dasbor Analitik**. Pilih indikator untuk melihat selisih tahunan dan gap target. Korelasi hanya ditampilkan jika tersedia sedikitnya empat pasangan tahun. Required run-rate merupakan ekstrapolasi linear sederhana, bukan proyeksi resmi.

![Halaman analitik](images/03-analitik.png)

## 4. Masuk sebagai admin/PIC

Buka **Admin**, masukkan akun, lalu pilih fungsi yang diperlukan. Kata sandi awal wajib diganti sebelum pemakaian kerja.

![Halaman login admin](images/04-admin.png)

## 5. Memperbarui satu nilai

1. Pilih indikator yang menjadi tanggung jawab tim.
2. Isi tahun, jenis, nilai, sumber, dan catatan.
3. Kirim. Nilai berstatus `MENUNGGU_VERIFIKASI` dan belum tampil publik.
4. Penanggung jawab tim memilih `DISETUJUI` atau `DITOLAK`.
5. Nilai yang disetujui masuk ke fakta publik dan tercatat pada audit log.

## 6. Mengunggah Excel baru

Panel **Unggah Excel indikator** ada di halaman admin, khusus peran ADMIN.

1. Pilih berkas `.xlsx`. Berkas wajib memuat sheet **Basis Data Indikator**
   (tepat 86 baris indikator) dan **Data Target-Realisasi**. Sheet nilai boleh
   terisi sebagian — tidak semua indikator harus punya angka.
2. Tekan **Pratinjau**. Berkas diarsipkan lalu dibandingkan dengan isi basis
   data; belum ada yang berubah pada tahap ini.
3. Periksa empat kartu ringkasan: indikator baru, indikator yang tidak ada di
   berkas, nilai berubah, dan **nilai dilindungi**.
4. Tekan **Setujui & muat** hanya bila pratinjau sudah benar. Sistem memuat
   dataset dalam satu transaksi dan menulis jejak audit.

**Arti "nilai dilindungi".** Angka yang sudah melewati alur usulan operator ->
verifikator dianggap lebih tepercaya daripada isi berkas Excel. Bila berkas
memuat angka berbeda untuk sel yang sama, barisnya ditampilkan terpisah dengan
badge nomor usulan asalnya dan **tidak** ikut ditimpa. Untuk mengubah angka
seperti itu, kirim usulan baru lewat alur verifikasi, bukan lewat unggahan.

Berkas selain `.xlsx` ditolak. `.xls` lama perlu disimpan ulang sebagai
`.xlsx` lebih dulu.

## 7. Mengunduh data

Tombol **Unduh paket data** menghasilkan ZIP berisi CSV seluruh dataset serta katalog metadata dalam XLSX dan PDF. Halaman detail menyediakan unduhan satu indikator.
