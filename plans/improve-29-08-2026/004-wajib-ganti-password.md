# 004 — Tegakkan ganti sandi awal dan minta sandi lama

Baca `plans/improve-29-08-2026/README.md` dan `AGENTS.md` sebelum mulai.

**Tujuan:** Akun dengan `harus_ganti_password=True` tidak bisa memakai rute istimewa sampai sandinya diganti. Penggantian sandi sendiri wajib mengirim sandi saat ini. Sandi lebih dari 128 karakter ditolak sebelum Argon2.

**Ditulis terhadap (awal):** `8b3ae9a`.
**Disesuaikan terhadap:** `4a7939f` (29 Agustus 2026). Bendera masih kosmetik. `AdminPage.jsx` sekarang juga memuat `UnggahExcelPanel` dan `IndikatorManager` — layar ganti sandi harus **keluar sebelum** ruang kerja itu dirender.

**Cek dulu:**

```text
git diff --stat 4a7939f..HEAD -- backend/app/deps.py backend/app/routers/auth.py backend/app/services/auth.py backend/app/security.py backend/app/routers/admin.py frontend/src/pages/AdminPage.jsx frontend/src/api/endpoints.js tests/api/test_keamanan_http.py tests/unit/test_keamanan.py
```

## Ringkasan

| | |
|---|---|
| Prioritas | P1 |
| Perkiraan | beberapa jam |
| Risiko ubahan | rendah |
| Bergantung pada | tidak ada |
| Cabang | `fix/wajib-ganti-password` |
| Pesan commit | `Tegakkan ganti sandi awal dan minta sandi lama` |

## Mengapa ini penting

Akun baru (CLI seed dan buatan admin) `harus_ganti_password=True`. Login tetap menerbitkan token akses penuh. `pengguna_saat_ini` / `wajib_peran` tidak membaca bendera itu. `AdminPage` menyimpan token dan memuat ruang kerja. Sandi seed yang tercetak tetap kredensial istimewa.

`POST /auth/ganti-password` hanya menerima `password_baru`. Siapa pun yang memegang token akses (termasuk XSS pada `localStorage`) bisa mengunci akun dengan sandi baru. Panjang sandi Form tidak dibatasi, lalu di-hash Argon2.

`docs/refactoring/auth-keamanan.md` sudah mensyaratkan ganti sandi login pertama. Benderanya saat ini hanya kosmetik.

## Keadaan sekarang

- `backend/app/repositories/pengguna.py` sekitar 82–89 — `buat(...): harus_ganti_password=True`.
- `backend/app/services/auth.py` sekitar 69–77 — muatan login memuat bendera tetapi tetap mengembalikan `access_token`.
- `backend/app/deps.py` sekitar 37–67:

```python
def wajib_peran(*peran: str):
    def dependency(pengguna: ProfilPengguna = Depends(pengguna_saat_ini)) -> ProfilPengguna:
        if pengguna.peran not in peran:
            raise HTTPException(403, "Akses tidak diizinkan")
        return pengguna
    return dependency
```

- `backend/app/routers/auth.py` 79–90 — `ganti_password(password_baru: str = Form(...), ...)` tanpa `password_lama`.
- `backend/app/services/auth.py` 119–123 — hash, commit, `wajib_ganti=False`.
- `backend/app/security.py` 40–56 — `PANJANG_PASSWORD_MINIMUM = 12`; `password_memenuhi_syarat` hanya cek minimum.
- `frontend/src/pages/AdminPage.jsx` 39–56 — `refresh()` memanggil `profilSaya()`, lalu **langsung** `wilayah()`, `capaianExplorer()`, dan `daftarUsulan()`. `catch` **menghapus token** (“Sesi berakhir”). Jika `daftarUsulan` mulai 403, login pertama terlihat seperti logout.
- `IndikatorManager` (baris 379) memuat `/admin/indikator` sendiri di `useEffect`. `UnggahExcelPanel` (baris 279) juga. Jangan merender keduanya selama bendera menyala — early-return layar ganti sandi sudah cukup, asal dipasang **sebelum** `return <Shell>`.
- `PasswordResetModal` = admin mereset sandi **orang lain**. Bukan layar ganti sandi login pertama; jangan dipakai ulang untuk ini.
- `frontend/src/api/endpoints.js` 37–38 — `gantiPassword` sudah POST FormData ke `/auth/ganti-password`.
- Akun benih API `harus_ganti_password=False` (`tests/api/conftest.py` sekitar 169) — tes login kontrak tetap 200.
- Fixture `auth` = admin. Pengguna berbendera di tes dibuat lewat `POST /api/v1/admin/pengguna`.

Service mengembalikan `Ditolak` / `Penolakan`; jangan impor FastAPI di `services/auth.py`. Jangan mencatat sandi atau token di log.

## Cakupan

**Boleh diubah:**
- `backend/app/security.py` — `PANJANG_PASSWORD_MAKSIMUM = 128`.
- `backend/app/deps.py` — `wajib_peran(..., izinkan_wajib_ganti: bool = False)`.
- `backend/app/routers/auth.py` — wajib `password_lama`; ganti-password memakai `izinkan_wajib_ganti=True`.
- `backend/app/services/auth.py` — verifikasi `password_lama`; lewati Argon2 untuk sandi login terlalu panjang.
- `frontend/src/pages/AdminPage.jsx` — layar ganti sandi; jangan panggil `daftarUsulan` selama bendera menyala.
- `tests/api/test_keamanan_http.py`, `tests/unit/test_keamanan.py`.

**Jangan diubah:**
- Token akses ke cookie httpOnly (Opsi B).
- Penyimpanan `jti` token segar / cabut saat logout.
- Header CSP / menyembunyikan `/api/docs`.
- Pencetakan sandi CLI seed.
- `routers/admin.py` kecuali ternyata menyalin cek panjang sendiri (sekarang lewat `password_layak` / `periksa_pembuatan`). CRUD indikator dan unggah Excel sudah di `main` — jangan diubah.
- `IndikatorManager.jsx`, `UnggahExcelPanel.jsx`, `PasswordResetModal.jsx`.

## Langkah

### 1. Tes dulu

`tests/unit/test_keamanan.py` (di samping `test_kebijakan_panjang_minimum`):
- `password_memenuhi_syarat("a"*128)` True; `"a"*129` False.

`tests/api/test_keamanan_http.py`:
- Masuk sebagai admin (`auth`), `POST /api/v1/admin/pengguna` username unik (mis. `operator.wajib.1`), `nama`, `password` ≥12 karakter, `peran=OPERATOR`, `wilayah_kode=6501`. Akun itu `harus_ganti_password=True`.
- Login sebagai akun itu → 200, `harus_ganti_password is True`.
- `GET /api/v1/admin/usulan` dengan tokennya → **403** (bukan 401).
- `POST /api/v1/auth/ganti-password` hanya `password_baru` → 422.
- `POST` dengan `password_lama` salah → 401, `detail` soal sandi saat ini.
- `POST` dengan `password_lama` benar + sandi baru ≥12 → 200; lalu `GET /api/v1/admin/usulan` → 200 (daftar operator boleh kosong).
- Login dengan sandi panjang 200 → **bukan** 500; 401 dengan `PESAN_KREDENSIAL_SALAH` yang sama. Jangan kirim badan bermegabyte.

**Cek:** tes ini gagal sebelum kode produksi diubah (usulan saat ini 200 untuk akun berbendera).

### 2. Batas panjang + verifikasi sandi lama

- `password_memenuhi_syarat`: `PANJANG_PASSWORD_MINIMUM <= len(password) <= PANJANG_PASSWORD_MAKSIMUM`.
- `masuk`: jika `len(password) > PANJANG_PASSWORD_MAKSIMUM`, anggap kredensial salah (401, `PESAN_KREDENSIAL_SALAH`) **tanpa** Argon2.
- Ubah `ganti_password(session, akun, password_baru, password_lama)` mengembalikan `dict | Ditolak`: jika `verifikasi_password` gagal, `Ditolak(401, "Kata sandi saat ini salah")`. Lalu hash/commit seperti sekarang.
- Router: `password_lama: str = Form(...)`, `password_baru: str = Form(...)`; jika `Ditolak`, `raise HTTPException`. Tetap cek `password_layak(password_baru)` untuk 422.

### 3. Gerbang `wajib_peran`

```python
def wajib_peran(*peran: str, izinkan_wajib_ganti: bool = False):
    def dependency(pengguna: ProfilPengguna = Depends(pengguna_saat_ini)) -> ProfilPengguna:
        if pengguna.peran not in peran:
            raise HTTPException(403, "Akses tidak diizinkan")
        if pengguna.harus_ganti_password and not izinkan_wajib_ganti:
            raise HTTPException(403, "Wajib mengganti kata sandi sebelum melanjutkan")
        return pengguna
    return dependency
```

Pemanggilan lama `wajib_peran(Peran.ADMIN)` tetap jalan (default kata kunci). Rute ganti-password: `Depends(wajib_peran(*PERAN_INTERNAL, izinkan_wajib_ganti=True))`.

Jangan taruh cek bendera di `pengguna_saat_ini` — `/auth/saya` dan `/auth/logout` harus tetap jalan.

**Cek:**

```text
python -m pytest tests/api/test_keamanan_http.py tests/api/test_kontrak.py tests/unit/test_keamanan.py -q
```

### 4. Gerbang frontend

Di `refresh()` pada `AdminPage.jsx` (bentuk sekarang sekitar 39–56):
1. `profilSaya()`
2. `setMe(profile)`
3. jika `profile.harus_ganti_password`, **return** — jangan panggil `wilayah()`, `capaianExplorer()`, `daftarUsulan()`, `daftarPengguna()`, `logAudit()`.

Setelah cabang `if(!me)` (sedang memeriksa sesi, sekitar 160–165), **sebelum** `return <Shell>` (sekitar 212): jika `me.harus_ganti_password`, tampilkan `LoginShell` berisi formulir `password_lama` + `password_baru`, kirim lewat `endpoints.gantiPassword(new FormData(...))`, lalu `refresh()`.

Early return itu juga mencegah `UnggahExcelPanel` / `IndikatorManager` terpasang (keduanya di dalam `Shell`). Jangan menambah hook setelah early return yang sudah ada.

**Cek:**

```text
cd frontend && pnpm test && pnpm lint
```

Kalau bisa buka aplikasi: masuk sebagai akun berbendera, pastikan layar ganti sandi muncul, pastikan ruang kerja muncul setelah ganti. Kalau tidak ada peramban, tulis di laporan bahwa hanya tes API yang dijalankan.

## Selesai bila semua ini benar

- [ ] Pengguna berbendera tidak bisa `GET /api/v1/admin/usulan` (403)
- [ ] `ganti-password` mewajibkan `password_lama`
- [ ] `password_memenuhi_syarat` menolak panjang > 128
- [ ] `AdminPage` tidak memanggil `daftarUsulan` selama bendera menyala (baca berkasnya)
- [ ] `python -m pytest tests/api/test_keamanan_http.py tests/api/test_kontrak.py tests/unit/test_keamanan.py -q` kode keluar 0
- [ ] `cd frontend && pnpm test && pnpm lint` kode keluar 0
- [ ] Baris 004 di `plans/improve-29-08-2026/README.md` menjadi `DONE`

## Berhenti dan tanya

- `wajib_peran` sudah mengecek bendera.
- `izinkan_wajib_ganti` merusak `Depends(wajib_peran(Peran.ADMIN))` — jangan membuat modul dependency kedua.
- Perubahan UI seolah butuh rute React baru — tetap di `AdminPage`.

## Catatan untuk peninjau

403 login pertama tidak boleh ditafsirkan `refresh()` sebagai “sesi berakhir”. Cabut token segar saat ganti sandi adalah tindak lanjut, bukan bagian plan ini.
