# 005 — Katalog publik hanya DISETUJUI; insight/peta memakai periode terbaru

Baca `plans/improve-29-08-2026/README.md` dan `AGENTS.md` sebelum mulai. **Kerjakan setelah plan 003 di folder yang sama selesai.**

**Tujuan:** (1) Indikator `MENUNGGU_VERIFIKASI` tidak muncul di GET `/indikator`, `/capaian`, ekspor, dan detail publik. (2) Kartu insight dan peta kabupaten memakai angka semester terbaru, sama seperti beranda.

**Ditulis terhadap (awal):** `8b3ae9a`.
**Disesuaikan terhadap:** `4a7939f` (29 Agustus 2026). CRUD admin **sudah ada** dan memakai `repo_indikator.cari()` yang sama dengan katalog publik — jangan menyaring `_terverifikasi` di `cari()` tanpa parameter, atau draf hilang dari halaman admin.

**Cek dulu:**

```text
git diff --stat 4a7939f..HEAD -- backend/app/repositories/indikator.py backend/app/repositories/nilai.py backend/app/services/capaian.py backend/app/services/ekspor.py backend/app/services/indikator.py backend/app/services/insight.py backend/app/services/explorer.py backend/app/routers/indikator.py tests/api/test_kontrak.py tests/integrasi/test_repositories.py
```

Jika 003 sudah masuk, `insight._seri` / `capaian.muatan` seharusnya memanggil `seri_teramati`. Jangan dikembalikan ke `seri()`.

## Ringkasan

| | |
|---|---|
| Prioritas | P1 |
| Perkiraan | beberapa jam |
| Risiko ubahan | rendah |
| Bergantung pada | plan 003 |
| Cabang | `fix/katalog-publik-periode` |
| Pesan commit | `Sembunyikan indikator belum disetujui dan samakan angka periode di insight` |

## Mengapa ini penting

Benih kontrak punya `IUP-002` berstatus `MENUNGGU_VERIFIKASI` dengan komentar: *“harus tidak pernah muncul di endpoint publik.”* `repo_indikator.cari` (GET `/indikator`) dan `daftar_ekspor` (GET `/capaian` + CSV/XLSX/ZIP) **tidak** memakai `_terverifikasi`. Explorer/validitas sudah. Draf bocor ke katalog publik dan unduhan.

Selain itu, kartu insight dan peta memakai `terakhir_terisi` / `ambil` yang memaksa `periode IS NULL`. Beranda memakai `seri()` dengan semester terakhir yang disetujui menang. Formulir operator meminta Semester 1/2 sebagai usulan terpisah. Wilayah yang hanya punya realisasi semester tampil di beranda dan `BELUM_ADA_DATA` di insight/peta.

## Keadaan sekarang

- `tests/api/conftest.py` 101–107 — `IUP-002` belum diverifikasi. Tidak ada tes yang menegaskan ia absen dari muatan publik. Benih tes tetap 5 baris (bukan 86 seed produksi).
- `backend/app/repositories/indikator.py` 28–30 — `_terverifikasi` sudah ada.
- `cari()` 94–122: `disaring(select(Indikator))` tanpa `_terverifikasi`. **Pemanggil:** `services/indikator.py` `cari()` (publik, baris 39–70) **dan** `daftar_admin()` (baris 428–451).
- `daftar_ekspor()` 125–128: semua baris, IUP lalu ISV. Pemanggil hanya publik (`capaian.daftar`, `ekspor`).
- `backend/app/routers/indikator.py` 52–57 — `detail_indikator` memakai `ambil`, bukan `ambil_terverifikasi`. Rute metadata (60–65) sudah `ambil_terverifikasi`. Detail admin (`routers/admin.py` 172–178) memakai `ambil` — **biarkan**.
- `backend/app/services/capaian.py` 286 — `daftar()` memakai `daftar_ekspor`.
- `backend/app/services/ekspor.py` 155, 219, 223 — sama.
- `backend/app/services/insight.py` 27–42 — `_kartu` memakai `terakhir_terisi` (tahunan). Overlay `nilai_periode_terbaru` hanya jika tahun tahunan itu ada. Perbandingan wilayah 113–118 memakai `ambil`.
- `backend/app/services/explorer.py` 109–113 — per kabupaten `ambil`.
- `backend/app/repositories/nilai.py` — `ambil` dan `terakhir_terisi` `tahunan=True`. `nilai_periode_terbaru` sudah ada.

Pembacaan publik di header `nilai.py`: hanya `DISETUJUI`. Samakan dengan `ambil_terverifikasi` pada detail capaian-explorer.

## Cakupan

**Boleh diubah:**
- `backend/app/repositories/indikator.py` — `cari(..., hanya_terverifikasi: bool = False)` dan `daftar_ekspor` memakai `_terverifikasi`.
- `backend/app/services/indikator.py` — `cari()` publik mengirim `hanya_terverifikasi=True`. `daftar_admin` **tetap** default `False`.
- `backend/app/routers/indikator.py` — detail memakai `ambil_terverifikasi`.
- `backend/app/repositories/nilai.py` — `nilai_tampil` dan `terakhir_terisi_termasuk_periode`.
- `backend/app/services/insight.py` — `_kartu` dan perbandingan memakai itu.
- `backend/app/services/explorer.py` — loop kabupaten memakai `nilai_tampil`.
- `tests/api/test_kontrak.py` — IUP-002 absen di publik; detail 404; `GET /admin/indikator` masih memuat IUP-002.
- `tests/api/conftest.py` — tambah satu indikator `DISETUJUI` tanpa nilai (`ISV-099`) agar tes capaian kosong tidak bergantung pada `IUP-002`.
- `tests/integrasi/test_repositories.py` — tes `nilai_tampil`.

**Jangan diubah:**
- `daftar_admin` / `detail_admin` / `routers/admin.py` CRUD kecuali tes yang menegaskan draf tetap terlihat.
- `IndikatorManager.jsx`.
- Isian celah beranda (plan 003).
- Frontend publik.
- Mengalihkan `_seri` / `capaian.muatan` dari fill (plan 003).
- `seed_massal` / `jumlah` / fixture `indikator_seed.json`.

## Langkah

### 1. Tes kebocoran dulu

Di `tests/api/test_kontrak.py`:

```python
def test_indikator_publik_tanpa_yang_belum_diverifikasi(_json, client):
    body = _json("/api/v1/indikator?page_size=200")
    ids = [x["id_indikator"] for x in body["data"]]
    assert "IUP-002" not in ids
    # Jangan assert total angka tetap: tes API berbagi DB sesi dengan CRUD admin.

def test_capaian_publik_tanpa_yang_belum_diverifikasi(_json, client):
    ids = [x["id_indikator"] for x in _json("/api/v1/capaian")["data"]]
    assert "IUP-002" not in ids

def test_detail_indikator_belum_diverifikasi_404(client):
    assert client.get("/api/v1/indikator/IUP-002/detail").status_code == 404

def test_ekspor_csv_tanpa_yang_belum_diverifikasi(client):
    teks = client.get("/api/v1/ekspor.csv").text
    assert "IUP-002" not in teks
```

Masih di `tests/api/test_kontrak.py` (jangan sisip ke `test_admin_indikator.py` — berkas itu tes CRUD berurutan di DB sesi yang sama):

```python
def test_admin_melihat_indikator_belum_diverifikasi(_json, client, auth):
    ids = [x["id_indikator"] for x in _json("/api/v1/admin/indikator?page_size=200", headers=auth)["data"]]
    assert "IUP-002" in ids
```

Tes admin ini **lulus** hari ini; ia mengunci agar saringan publik tidak merembes ke CRUD.

**Cek:** empat tes publik gagal hari ini (IUP-002 muncul / detail 200). Tes admin hijau.

### 2. Saring `DISETUJUI` tanpa merusak admin

`cari` **tidak** boleh selalu menyaring: `daftar_admin` memakainya untuk draf. Tambah parameter:

```python
def cari(
    session: Session,
    *,
    q: str | None = None,
    kategori: Sequence[str] | None = None,
    kelompok: Sequence[str] | None = None,
    tim: Sequence[str] | None = None,
    status_metadata: Sequence[str] | None = None,
    sort: str = "id_indikator",
    order: str = "asc",
    page: int = 1,
    page_size: int = 25,
    hanya_terverifikasi: bool = False,
) -> tuple[list[Indikator], int]:
    ...
    stmt = disaring(select(Indikator))
    hitung = disaring(select(func.count()).select_from(Indikator))
    if hanya_terverifikasi:
        stmt = _terverifikasi(stmt)
        hitung = _terverifikasi(hitung)
    daftar = session.scalars(
        stmt.order_by(arah(kolom)).offset((page - 1) * page_size).limit(page_size)
    ).all()
    total = session.scalar(hitung) or 0
```

`services/indikator.py` `cari()` (publik): `repo_indikator.cari(..., hanya_terverifikasi=True)`.
`daftar_admin`: jangan kirim flag itu (default `False`).

`daftar_ekspor` (hanya pemanggil publik):

```python
stmt = _terverifikasi(select(Indikator)).order_by(Indikator.kategori.desc(), Indikator.nomor)
```

Router publik `detail_indikator`: `ambil_terverifikasi`; pesan 404 tetap `"Indikator tidak ditemukan"`.

Jangan ubah `ambil()` (pencarian PK internal + detail admin).

**Cek:**

```text
python -m pytest tests/api/test_kontrak.py tests/api/test_admin_indikator.py -q
```

`test_admin_indikator.py` tidak diubah, tetapi wajib tetap hijau (CRUD berbagi DB sesi dengan tes kontrak).

### 3. Pembantu “periode menang”

Di `repositories/nilai.py`:

```python
def nilai_tampil(
    session: Session,
    id_indikator: str,
    wilayah_kode: str,
    tahun: int,
    jenis: str = JenisNilai.REALISASI,
) -> NilaiIndikator | None:
    """Angka yang ditampilkan: rilis periode terbaru, atau tahunan bila tidak ada."""
    periodik = nilai_periode_terbaru(session, id_indikator, wilayah_kode, tahun, jenis)
    if periodik is not None:
        return periodik
    return ambil(session, id_indikator, wilayah_kode, tahun, jenis)


def terakhir_terisi_termasuk_periode(
    session: Session,
    id_indikator: str,
    wilayah_kode: str,
    sampai_tahun: int,
    jenis: str = JenisNilai.REALISASI,
) -> NilaiIndikator | None:
    """Nilai terisi paling akhir, tahunan atau periodik, hingga sampai_tahun."""
    stmt = (
        _lingkup(select(NilaiIndikator), id_indikator, wilayah_kode, jenis, tahunan=False)
        .where(
            NilaiIndikator.tahun <= sampai_tahun,
            (NilaiIndikator.nilai.is_not(None)) | (NilaiIndikator.nilai_teks.is_not(None)),
        )
        .order_by(NilaiIndikator.tahun.desc(), NilaiIndikator.periode.desc().nullslast())
        .limit(1)
    )
    return session.scalars(stmt).first()
```

Insight `_kartu`: ganti `terakhir_terisi` → `terakhir_terisi_termasuk_periode`. Loop perbandingan: `nilai_tampil(..., tahun_aktif, JenisNilai.REALISASI)` bukan `ambil`.

Explorer loop kabupaten: `nilai_tampil` untuk nilai dan target.

Tes `tests/integrasi/test_repositories.py::test_nilai_tampil_memilih_semester`: tahunan 2025=1.0, semester 2=3.0 → `nilai_tampil` == 3.0. Hanya semester, tanpa tahunan → tetap 3.0. Pakai `_sisip_nilai` / `indikator_uji` (lihat tes periode sekitar baris 180). `test_indikator_cari_saring_dan_paginasi` / `test_indikator_cari_urut_menurun` memakai `cari()` tanpa flag — default `hanya_terverifikasi=False` supaya tetap hijau.

`test_capaian_tanpa_data_bukan_nol` di `tests/api/test_kontrak.py` sekitar 236–242 sekarang mengandalkan `IUP-002` (draf, tanpa nilai). Setelah `daftar_ekspor` tersaring, keempat indikator disetujui benih **punya** nilai. Tambah di `_isi_benih` (`tests/api/conftest.py`) satu indikator `DISETUJUI` tanpa baris `nilai_indikator`, mis. `ISV-099` "Tanpa Realisasi", agar tes itu tetap punya baris `nilai_terakhir is None`. Jangan longgarkan assersi `BELUM_ADA_DATA`.

**Cek:**

```text
python -m pytest tests/integrasi/test_repositories.py tests/api/test_kontrak.py -q
ruff check backend/app/repositories/indikator.py backend/app/repositories/nilai.py backend/app/services/insight.py backend/app/services/explorer.py backend/app/routers/indikator.py
```

## Selesai bila semua ini benar

- [ ] `IUP-002` tidak muncul di `/indikator`, `/capaian`, `/ekspor.csv`
- [ ] `GET /api/v1/admin/indikator` (auth admin) **masih** memuat `IUP-002`
- [ ] `/indikator/IUP-002/detail` = 404
- [ ] `nilai_tampil` diuji untuk hanya-periode dan periode-mengalahkan-tahunan
- [ ] `insight.py` dan `explorer.py` tidak memakai `ambil` untuk realisasi kabupaten (memakai `nilai_tampil`)
- [ ] `python -m pytest tests/api/test_kontrak.py tests/api/test_admin_indikator.py tests/integrasi/test_repositories.py -q` kode keluar 0
- [ ] `test_admin_indikator.py` tidak diubah (urutan CRUD sesi tetap)
- [ ] Jika 003 sudah `DONE`, pemanggilan `seri_teramati` masih ada
- [ ] Baris 005 di `plans/improve-29-08-2026/README.md` menjadi `DONE`

```text
rg "repo_nilai\\.ambil\\(" backend/app/services/insight.py backend/app/services/explorer.py
```

## Berhenti dan tanya

- `cari` sudah menyaring `_terverifikasi` **tanpa** parameter — itu akan menyembunyikan draf di `GET /admin/indikator`. Jangan diteruskan; pakai `hanya_terverifikasi`.
- `daftar_admin` ternyata memakai `daftar_ekspor` (sekarang tidak) — tanya dulu.
- Plan 003 belum masuk dan Anda hendak menulis ulang perilaku fill `_seri` — jangan; biarkan `_seri` ke 003.

## Catatan untuk peninjau

CRUD admin sudah di `main` lewat `daftar_admin` → `repo_indikator.cari()` tanpa filter status. AnalyticsPage memakai `/capaian` sebagai katalog dropdown; setelah ini hanya indikator disetujui yang tampil — itu benar. Tambah tes agar `GET /admin/indikator` tidak ikut tersaring.
