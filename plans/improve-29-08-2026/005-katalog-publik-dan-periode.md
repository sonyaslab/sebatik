# 005 — Katalog publik hanya DISETUJUI; insight/peta memakai periode terbaru

Baca `plans/improve-29-08-2026/README.md` dan `AGENTS.md` sebelum mulai. **Kerjakan setelah plan 003 di folder yang sama selesai.**

**Tujuan:** (1) Indikator `MENUNGGU_VERIFIKASI` tidak muncul di GET `/indikator`, `/capaian`, ekspor, dan detail publik. (2) Kartu insight dan peta kabupaten memakai angka semester terbaru, sama seperti beranda.

**Ditulis terhadap:** commit `8b3ae9a`.

**Cek dulu:**

```text
git diff --stat 8b3ae9a..HEAD -- backend/app/repositories/indikator.py backend/app/repositories/nilai.py backend/app/services/capaian.py backend/app/services/ekspor.py backend/app/services/indikator.py backend/app/services/insight.py backend/app/services/explorer.py backend/app/routers/indikator.py tests/api/test_kontrak.py tests/integrasi/test_repositories.py
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

- `tests/api/conftest.py` sekitar 101–107 — `IUP-002` belum diverifikasi. Tidak ada tes yang menegaskan ia absen dari muatan publik.
- `backend/app/repositories/indikator.py` sekitar 28–30 — `_terverifikasi` sudah ada.
- `cari()` sekitar 92–95: `disaring(select(Indikator))` tanpa `_terverifikasi`.
- `daftar_ekspor()` sekitar 99–102: semua baris, IUP lalu ISV.
- `backend/app/routers/indikator.py` sekitar 52–57 — `detail_indikator` memakai `ambil`, bukan `ambil_terverifikasi`. Rute metadata sudah `ambil_terverifikasi`.
- `backend/app/services/capaian.py` sekitar 286 — `daftar()` memakai `daftar_ekspor`.
- `backend/app/services/ekspor.py` sekitar 155, 219, 223 — sama.
- `backend/app/services/insight.py` sekitar 27–42 — `_kartu` memakai `terakhir_terisi` (tahunan). Overlay periode hanya jika tahun tahunan itu ada. Perbandingan wilayah sekitar 113–118 memakai `ambil`.
- `backend/app/services/explorer.py` sekitar 109–113 — per kabupaten `ambil`.
- `backend/app/repositories/nilai.py` — `ambil` dan `terakhir_terisi` `tahunan=True`. `nilai_periode_terbaru` sudah ada.

Pembacaan publik di header `nilai.py`: hanya `DISETUJUI`. Samakan dengan `ambil_terverifikasi` pada detail capaian-explorer.

## Cakupan

**Boleh diubah:**
- `backend/app/repositories/indikator.py` — `cari` dan `daftar_ekspor` memakai `_terverifikasi`.
- `backend/app/routers/indikator.py` — detail memakai `ambil_terverifikasi`.
- `backend/app/repositories/nilai.py` — `nilai_tampil` dan `terakhir_terisi_termasuk_periode`.
- `backend/app/services/insight.py` — `_kartu` dan perbandingan memakai itu.
- `backend/app/services/explorer.py` — loop kabupaten memakai `nilai_tampil`.
- `tests/api/test_kontrak.py` — IUP-002 absen; detail 404.
- `tests/integrasi/test_repositories.py` — tes `nilai_tampil`.

**Jangan diubah:**
- Tampilan admin untuk draf (CRUD plan B nanti **jangan** memakai `daftar_ekspor`; tambah `daftar_semua` hanya jika ada pemanggil admin **sekarang** — lihat “berhenti”).
- Isian celah beranda (plan 003).
- Frontend.
- Mengalihkan `_seri` / `capaian.muatan` dari fill (plan 003).

## Langkah

### 1. Tes kebocoran dulu

Di `tests/api/test_kontrak.py`:

```python
def test_indikator_publik_tanpa_yang_belum_diverifikasi(_json, client):
    body = _json("/api/v1/indikator?page_size=200")
    assert all(x["id_indikator"] != "IUP-002" for x in body["data"])
    assert body["total"] == 4  # benih: 5 baris, 4 disetujui

def test_capaian_publik_tanpa_yang_belum_diverifikasi(_json, client):
    ids = [x["id_indikator"] for x in _json("/api/v1/capaian")["data"]]
    assert "IUP-002" not in ids

def test_detail_indikator_belum_diverifikasi_404(client):
    assert client.get("/api/v1/indikator/IUP-002/detail").status_code == 404

def test_ekspor_csv_tanpa_yang_belum_diverifikasi(client):
    teks = client.get("/api/v1/ekspor.csv").text
    assert "IUP-002" not in teks
```

**Cek:** tes ini gagal hari ini (IUP-002 muncul / detail 200).

### 2. Saring `DISETUJUI`

`cari` — bungkus query halaman dan hitungan:

```python
daftar = session.scalars(
    _terverifikasi(disaring(select(Indikator))).order_by(arah(kolom)).offset((page - 1) * page_size).limit(page_size)
).all()
total = session.scalar(_terverifikasi(disaring(select(func.count()).select_from(Indikator)))) or 0
```

`daftar_ekspor`:

```python
stmt = _terverifikasi(select(Indikator)).order_by(Indikator.kategori.desc(), Indikator.nomor)
```

Router `detail_indikator`: `ambil_terverifikasi`; pesan 404 tetap `"Indikator tidak ditemukan"`.

Jangan ubah `ambil()` (pencarian PK internal).

**Cek:**

```text
python -m pytest tests/api/test_kontrak.py -q
```

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

Tes `tests/integrasi/test_repositories.py::test_nilai_tampil_memilih_semester`: tahunan 2025=1.0, semester 2=3.0 → `nilai_tampil` == 3.0. Hanya semester, tanpa tahunan → tetap 3.0. Pakai `_sisip_nilai` / `indikator_uji` (lihat tes periode sekitar baris 180).

**Cek:**

```text
python -m pytest tests/integrasi/test_repositories.py tests/api/test_kontrak.py -q
ruff check backend/app/repositories/indikator.py backend/app/repositories/nilai.py backend/app/services/insight.py backend/app/services/explorer.py backend/app/routers/indikator.py
```

## Selesai bila semua ini benar

- [ ] `IUP-002` tidak muncul di `/indikator`, `/capaian`, `/ekspor.csv`
- [ ] `/indikator/IUP-002/detail` = 404
- [ ] `nilai_tampil` diuji untuk hanya-periode dan periode-mengalahkan-tahunan
- [ ] `insight.py` dan `explorer.py` tidak memakai `ambil` untuk realisasi kabupaten (memakai `nilai_tampil`)
- [ ] `python -m pytest tests/api/test_kontrak.py tests/integrasi/test_repositories.py -q` kode keluar 0
- [ ] Jika 003 sudah `DONE`, pemanggilan `seri_teramati` masih ada
- [ ] Baris 005 di `plans/improve-29-08-2026/README.md` menjadi `DONE`

```text
rg "repo_nilai\\.ambil\\(" backend/app/services/insight.py backend/app/services/explorer.py
```

## Berhenti dan tanya

- `cari` sudah menyaring `_terverifikasi`.
- Ada pemanggil admin **sekarang** (bukan CRUD masa depan) ke `daftar_ekspor` yang harus melihat draf — tambah `daftar_semua` hanya untuk pemanggil itu, atau tanya jika tidak yakin.
- Plan 003 belum masuk dan Anda hendak menulis ulang perilaku fill `_seri` — jangan; biarkan `_seri` ke 003.

## Catatan untuk peninjau

CRUD admin indikator (`docs/superpowers/plans/2026-08-27-admin-manajemen-indikator.md`) harus mendaftar **semua** baris lewat fungsi repository baru, bukan `daftar_ekspor`. AnalyticsPage memakai `/capaian` sebagai katalog dropdown; setelah ini hanya indikator disetujui yang tampil — itu benar.
