# Rencana: Unggah Excel Indikator oleh Admin

Status: **sudah dieksekusi** (lihat CHANGELOG "Unggah Excel indikator oleh admin")

Catatan pelaksanaan: §3 menyatakan tidak ada logika pemetaan baru yang perlu
ditulis karena nama sheet dan kolomnya sama persis dengan yang sudah dibaca
`transformasi_sumber_database()`. Itu benar untuk nama kolom, tetapi fungsi
tersebut menggabungkan kedua sheet lewat `ID Indikator` — dan penomoran IUP
kedua sheet berbeda, sehingga nilai menempel ke indikator yang salah. Kunci
gabung diperbaiki menjadi `(Kategori, Kode Indikator)` saat eksekusi; tanpa
itu kriteria idempoten di §8 langkah 4 tidak pernah terpenuhi.
Sumber data acuan: `data/raw/BASIS_DATA_INDIKATOR_ISV-IUP_KALTARA.xlsx`

---

## 1. Latar belakang

Admin SEBATIK belum bisa mengisi atau memperbarui 86 indikator secara mandiri.
Rantai data hari ini terdiri atas tiga langkah, dan dua di antaranya hanya bisa
dijalankan dari terminal oleh developer:

```
BASIS_DATA_INDIKATOR_ISV-IUP_KALTARA.xlsx
  → [offline] tools/import_classified_workbook.py     → data/raw/*.json
  → [offline] scripts/kelola_database.py transformasi → sebatik-database.json
  → [API]     POST /admin/unggah/pratinjau → setujui  → muat_dataset()
```

Ada dua masalah nyata:

1. **Backend unggah sudah lengkap tetapi tidak punya antarmuka.**
   `pratinjauUnggahan` dan `setujuiUnggahan` sudah tersedia di
   `frontend/src/api/endpoints.js` namun tidak dipanggil dari mana pun di
   `frontend/src`. Fiturnya praktis mati.
2. **Admin non-teknis terkunci di langkah 1–2.** Endpoint hanya menerima `.json`
   berformat `sebatik.database/v1`, bentuk yang tidak mungkin dibuat admin tanpa
   menjalankan CLI.

Hasil yang diinginkan: admin membuka halaman admin, memilih berkas `.xlsx`,
melihat pratinjau perubahan, lalu menyetujui — tanpa menyentuh terminal.

---

## 2. Keputusan desain

| Topik | Keputusan |
|---|---|
| Lingkup | Unggah Excel massal lewat UI admin (bukan form per-indikator) |
| Format API | Endpoint unggah **hanya menerima `.xlsx`**; jalur `.json` di HTTP dihapus |
| Kelengkapan | Sheet master wajib tepat 86 indikator; sheet nilai boleh parsial |
| Konflik | Nilai hasil verifikasi (`usulan_id` terisi) **dilindungi**, dilaporkan di pratinjau |

### Asumsi yang perlu dikonfirmasi sebelum eksekusi

- "Hanya `.xlsx`" ditafsirkan berlaku untuk **endpoint HTTP**.
  `scripts/kelola_database.py` tetap mempertahankan subperintah
  `transformasi/validasi/muat` berbasis JSON karena dipakai jalur deployment
  container dan CI (lihat `docs/11-prosedur-etl-database.md`). CLI justru
  **ditambah** subperintah `excel` supaya CLI dan API memakai satu konverter yang
  sama. Bila yang dimaksud jalur JSON di CLI ikut dihapus, keputusan ini perlu
  direvisi lebih dulu.
- Rencana ini **membalik aturan** yang tertulis di docstring `src/etl/database.py`
  ("Excel dan PDF berhenti di zona sumber"), `README.md`, dan
  `docs/11-prosedur-etl-database.md`. Gerbang validasi (`validasi_dataset`) tetap
  dilewati penuh — yang berubah hanya *di mana* konversi terjadi, bukan seberapa
  ketat data diperiksa. Dokumen-dokumen tersebut wajib ikut diperbarui agar tidak
  bertentangan dengan kode.

---

## 3. Struktur Excel yang menjadi kontrak

Sudah diverifikasi langsung terhadap berkas nyata:

- Sheet **`Basis Data Indikator`** — header di baris 1, **86 baris data**, 35 kolom.
- Sheet **`Data Target-Realisasi`** — header di baris 1, **660 baris data**, 10 kolom:
  `ID Indikator`, `Kategori`, `Kelompok / Pilar`, `Kode Indikator`,
  `Nama Indikator (Kaltara)`, `Jenis Nilai`, `Tahun`, `Nilai (Angka)`,
  `Nilai (Teks Asli)`, `Satuan/Catatan`.

Nama sheet dan nama kolom ini **persis sama** dengan yang sudah dibaca
`transformasi_sumber_database()`. Artinya tidak ada logika pemetaan baru yang
perlu ditulis — cukup adaptor `.xlsx → dict` di depannya.

Kolom Excel yang sengaja **tidak** dipetakan karena bersifat turunan:
`Jumlah Tahun Realisasi Terisi`, `Kelengkapan Realisasi (%)`,
`Status Ketersediaan Realisasi`, `Selisih Realisasi 2025 – Target 2025`.

---

## 4. Perubahan backend

### 4.1 `src/etl/excel.py` (baru) — adaptor Excel → bentuk sumber

Satu fungsi publik, memindahkan logika `tools/import_classified_workbook.py` ke
modul yang dapat diimpor:

```python
SHEET_WAJIB = ("Basis Data Indikator", "Data Target-Realisasi")

def baca_workbook(isi: bytes, nama_berkas: str) -> dict[str, Any]:
    """Ubah byte .xlsx menjadi bentuk {"source": ..., "sheets": {...}}."""
```

- `load_workbook(BytesIO(isi), data_only=True, read_only=True)` — `data_only`
  wajib agar sel berumus terbaca sebagai nilai, sama seperti tool lama.
- Sheet hilang → `DatasetTidakValid("Sheet 'X' tidak ditemukan di workbook")`.
- Byte bukan zip/xlsx valid → tangkap `InvalidFileException` dan
  `zipfile.BadZipFile`, ubah menjadi `DatasetTidakValid` berbahasa Indonesia.
- Selalu `workbook.close()` — mode `read_only` menahan handle berkas.

Keluarannya langsung diumpankan ke `transformasi_sumber_database()` yang sudah
ada. `tools/import_classified_workbook.py` direfaktor agar memanggil modul ini
supaya tidak ada dua salinan logika baca.

### 4.2 `src/etl/database.py` — konverter gabungan + dukungan lewati-konflik

- Tambah `transformasi_workbook_excel(isi: bytes, nama: str) -> dict` =
  `transformasi_sumber_database(baca_workbook(isi, nama))`. Titik masuk tunggal
  untuk API maupun CLI.
- Tambah parameter `muat_dataset(session, dataset, *, lewati_nilai=None)`.
  `lewati_nilai` berisi kunci `(id_indikator, wilayah_kode, tahun, jenis, periode)`
  yang **tidak** boleh di-upsert. Kembalikan juga jumlah yang dilewati pada dict
  hasil (`{"nilai_dilewati": n}`). Default `None` menjaga perilaku CLI lama.
- `validasi_dataset()` **tidak berubah**: master tetap wajib tepat 86 ID unik
  (`JUMLAH_INDIKATOR`), sedangkan `nilai_indikator` memang sudah tidak punya
  batas bawah — jadi "nilai boleh parsial" sudah terpenuhi tanpa perubahan kode.
  Tambahkan komentar eksplisit agar aturan ini tidak hilang saat dibaca ulang.
- Longgarkan docstring modul: Excel kini diterima di gerbang API, tetapi tetap
  harus lolos `validasi_dataset()` sebelum menyentuh basis data.

### 4.3 `backend/app/services/unggahan.py` — ekstensi, arsip, konflik

- Ganti `berekstensi_database()` → `berekstensi_excel(nama)`: hanya `.xlsx`.
  `.xls` ditolak dengan pesan khusus ("simpan ulang sebagai .xlsx") karena
  openpyxl tidak membacanya.
- `arsipkan(isi)` menulis `{ts}-{uuid}.xlsx`, bukan `.database.json`.
- `_baca_dataset(path)` → `_dataset_dari_arsip(path)`: baca byte `.xlsx` lalu
  panggil `transformasi_workbook_excel`. Pratinjau dan penerapan mem-parsing
  ulang berkas arsip yang sama — 86 + 660 baris, biayanya milidetik, dan cara ini
  menghindari penambahan kolom baru di tabel `unggahan_excel` (tanpa migrasi).
- **Deteksi konflik** pada `susun_diff()`: `repo_nilai.semua_nilai_provinsi()`
  sudah mengembalikan objek `NilaiIndikator` lengkap, sehingga `baris.usulan_id`
  langsung terbaca — tidak perlu query baru. Pisahkan hasil menjadi:
  - `nilai_berubah` — baris lama tanpa `usulan_id`, atau baris baru → akan dimuat.
  - `nilai_konflik` — baris lama dengan `usulan_id` terisi dan nilainya berbeda →
    **tidak** dimuat, dilaporkan beserta `usulan_id`.
- `terapkan()` menghitung ulang himpunan konflik (jangan percaya `ringkasan_diff`
  yang tersimpan — basis data bisa berubah antara pratinjau dan persetujuan),
  meneruskannya sebagai `lewati_nilai` ke `muat_dataset`, dan mencatat
  `LogPerubahan` hanya untuk baris yang benar-benar termuat. Tambahkan satu
  catatan aktivitas berisi jumlah konflik yang dilewati.

### 4.4 `backend/app/schemas/unggahan.py`

```python
class NilaiKonflik(NilaiBerubah):
    usulan_id: int | None = None

class RingkasanUnggahan(BaseModel):
    indikator: int
    nilai_dimuat: int
    nilai_dilindungi: int

class DiffUnggahan(BaseModel):
    indikator_baru: list[str]
    indikator_hilang: list[str]
    nilai_berubah: list[NilaiBerubah]
    nilai_konflik: list[NilaiKonflik]   # baru
    ringkasan: RingkasanUnggahan        # baru

class RiwayatUnggahan(BaseModel): ...   # id, nama_file_asli, status, dibuat_pada, oleh
class RiwayatUnggahanResponse(BaseModel):
    data: list[RiwayatUnggahan]
```

`tests/api/test_kontrak_openapi.py` mewajibkan setiap endpoint JSON memiliki
`response_model` bernama — seluruh skema di atas memenuhinya.

### 4.5 `backend/app/routers/unggahan.py`

- Pesan galat dan pengecekan ekstensi mengikuti `berekstensi_excel`.
- Tambah `GET /api/v1/admin/unggah` (admin-only) → `RiwayatUnggahanResponse`,
  berisi 10 unggahan terakhir, agar UI dapat menampilkan riwayat.
- Query-nya ditempatkan di `repositories/tata_kelola.py` (`daftar_unggahan`),
  **bukan** di router. `tests/unit/test_arsitektur.py` menolak router yang
  memanggil `select()`, memakai `for`/`while`, atau merakit dict lebih dari 5
  kunci. Pemetaan baris → skema harus berupa comprehension satu tingkat atau
  dipindah ke service.

### 4.6 `scripts/kelola_database.py`

Tambah subperintah `excel <sumber.xlsx> <keluaran.json>` yang memanggil
`transformasi_workbook_excel`. Subperintah lama tetap ada. Tangkap juga
`DatasetTidakValid` dari jalur Excel pada blok `except` yang sudah ada.

---

## 5. Perubahan frontend

### 5.1 `frontend/src/components/admin/UnggahExcelPanel.jsx` (baru)

Komponen mandiri mengikuti pola `SubmissionTable.jsx` dan
`PasswordResetModal.jsx` — function component, props `{onNotify, onSelesai}`,
tidak pernah memanggil `fetch` langsung.

Tiga keadaan:

1. **Pilih berkas** — `<input type="file" accept=".xlsx">` dan tombol
   "Pratinjau". Tombol dinonaktifkan selama unggah; tampilkan status
   "Memproses…" karena parsing dan diff dapat memakan 1–2 detik.
2. **Pratinjau** — kartu ringkasan (indikator baru / hilang / nilai berubah /
   **nilai dilindungi**), lalu dua tabel di dalam `.table-scroll`:
   - *Nilai berubah*: `ID · Tahun · Jenis · Lama → Baru`
   - *Nilai dilindungi*: kolom sama, ditambah badge "hasil verifikasi #usulan_id"
     dan keterangan bahwa baris ini **tidak** akan ditimpa. Sembunyikan tabel ini
     bila kosong.

   Batasi render pada 200 baris pertama per tabel dengan catatan "… dan N
   lainnya" — diff penuh bisa ratusan baris dan akan memberatkan halaman.
   Tombol "Setujui & muat" (destruktif, minta konfirmasi) dan "Batal".
3. **Selesai** — panggil `onSelesai()` agar `AdminPage.refresh()` menarik ulang
   log audit, lalu kembali ke keadaan 1.

Galat 422 (`error.detail`) ditampilkan apa adanya — pesan validasinya sudah
berbahasa Indonesia dan spesifik, misalnya "Master harus berisi tepat 86 ID unik".

### 5.2 `frontend/src/pages/AdminPage.jsx`

Sisipkan `<UnggahExcelPanel onNotify={notify} onSelesai={refresh}/>` pada cabang
`me?.peran==='ADMIN'`, setelah `<Panel>` daftar akun. Gunakan `notify`/`notifyOk`
yang sudah ada; jangan membuat state pesan baru.

### 5.3 `frontend/src/api/endpoints.js`

`pratinjauUnggahan` dan `setujuiUnggahan` sudah benar (`body: FormData`,
`autentikasi:'wajib'`). Tambahkan:

```js
export const riwayatUnggahan = () => request(`${V1}/admin/unggah`, wajib)
```

### 5.4 `frontend/src/styles.css`

Kelas untuk badge konflik dan panah lama→baru. Gunakan token warna yang sudah ada
(`tokens.js`, `indicator-state`, `notice warning`); jangan menulis hex langsung.

---

## 6. Tes

### `tests/etl/test_excel.py` (baru)

Helper `_workbook_uji(jumlah=86)` membangun `.xlsx` di memori dengan openpyxl
(header persis sama dengan berkas nyata), lalu menguji:

- konversi berhasil, manifest = 86 indikator + N nilai;
- sheet hilang → `DatasetTidakValid`;
- byte sampah → `DatasetTidakValid`, bukan traceback openpyxl;
- 85 baris master → ditolak;
- **nilai kosong/parsial → diterima** (poin kunci keputusan §2).

### `tests/etl/test_database.py` (tambah)

`muat_dataset(..., lewati_nilai={...})` tidak menyentuh baris yang dilewati dan
melaporkannya pada dict hasil.

### `tests/api/test_unggahan.py` (baru)

Memakai fixture `client`/`auth` dari `tests/api/conftest.py`. Catatan penting:
seed di sana hanya berisi 5 indikator sedangkan validasi membutuhkan 86 — jadi
tes API memakai workbook sintetis 86 baris dan mengharapkan sebagian besar masuk
sebagai `indikator_baru`. Kasus uji:

- `.json` / `.csv` → 422; berkas > 30 MB → 413;
- non-admin → 403; tanpa token → 401;
- pratinjau mengembalikan `id` + `diff` dengan `nilai_konflik` kosong;
- **konflik**: seed sudah memiliki satu usulan disetujui — pastikan baris
  ber-`usulan_id` muncul di `nilai_konflik` dan nilainya **tidak berubah**
  setelah `setujui`;
- `setujui` dua kali → 404 (unggahan sudah tidak berstatus menunggu).

### `frontend/src/components/admin/UnggahExcelPanel.test.jsx` (baru)

Pola vitest seperti `ui.test.jsx`: mock `endpoints`, render, pastikan tabel
konflik muncul dan tombol setujui memanggil endpoint yang benar.

---

## 7. Dokumentasi yang harus ikut diperbarui

- `docs/11-prosedur-etl-database.md` — tambah jalur "unggah Excel via UI admin"
  berdampingan dengan jalur CLI; perbaiki §1 yang menyatakan produksi tidak
  pernah membaca Excel.
- `README.md` (bagian jalur data) — sama.
- `docs/panduan-pengguna.md` §6 "Mengunggah Excel baru" — tulis ulang sesuai alur
  nyata, termasuk penjelasan arti "nilai dilindungi".
- `AGENTS.md` dan `docs/10-diagram-sistem.md` — perbarui deskripsi alur.
- `CHANGELOG.md` — satu entri.

---

## 8. Verifikasi

1. **Lint, tipe, dan tes**

   ```bash
   .venv-sebatik/Scripts/python.exe -m ruff check . && .venv-sebatik/Scripts/python.exe -m ruff format --check . && .venv-sebatik/Scripts/python.exe -m mypy backend src && .venv-sebatik/Scripts/python.exe -m pytest --cov --cov-fail-under=80
   ```

2. **Konversi berkas nyata lewat CLI** — bukti pemetaan kolom benar:

   ```bash
   .venv-sebatik/Scripts/python.exe -m scripts.kelola_database excel "data/raw/BASIS_DATA_INDIKATOR_ISV-IUP_KALTARA.xlsx" tmp/dataset-uji.json
   ```

   Harus mencetak `manifest={'indikator': 86, 'metadata_indikator': 86, 'nilai_indikator': ~660}`.

3. **Bandingkan dengan dataset lama** — `checksum_data` hasil langkah 2 harus sama
   dengan `data/processed/sebatik-database.json`. Kolom `source` akan berbeda
   karena nama berkas, jadi bandingkan bagian `data`-nya saja. Bila berbeda,
   pemetaan kolom menyimpang dari jalur lama dan harus diselidiki sebelum lanjut.

4. **Uji end-to-end di aplikasi**

   ```bash
   ./jalankan-sebatik.ps1
   ```

   Login sebagai admin → unggah `BASIS_DATA_INDIKATOR_ISV-IUP_KALTARA.xlsx` →
   pratinjau harus menampilkan 0 indikator baru dan 0 nilai berubah bila basis
   data sudah berisi dataset yang sama (sifat idempoten, sesuai
   `docs/07-jalur-data-report.md`).

5. **Uji perlindungan konflik secara manual** — ubah satu nilai lewat alur
   operator → verifikator, lalu unggah Excel berisi angka berbeda untuk sel yang
   sama. Pratinjau harus menampilkannya di tabel "nilai dilindungi", dan setelah
   disetujui, `SELECT nilai FROM nilai_indikator WHERE …` harus tetap berisi
   angka hasil verifikasi.

6. **Uji penolakan** — unggah `.json`, `.xls`, dan berkas teks yang diganti nama
   menjadi `.xlsx`. Ketiganya harus menghasilkan 422 dengan pesan berbahasa
   Indonesia, bukan 500.
