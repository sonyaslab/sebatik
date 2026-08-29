# 001 — Izinkan usulan tahunan ketika periode formulir kosong

Baca `plans/improve-29-08-2026/README.md` dan `AGENTS.md` sebelum mulai.

**Tujuan:** Operator yang mengirim realisasi **tahunan** (pilihan bawaan formulir) mendapat HTTP 200 dan baris usulan dengan `periode` NULL, bukan 422.

**Ditulis terhadap:** commit `8b3ae9a` (29 Agustus 2026).

**Cek dulu** (jika ada diff, berhenti dan tanya):

```text
git diff --stat 8b3ae9a..HEAD -- backend/app/routers/usulan.py backend/app/services/verifikasi.py frontend/src/pages/AdminPage.jsx tests/api/test_kontrak.py tests/api/conftest.py
```

## Ringkasan

| | |
|---|---|
| Prioritas | P1 |
| Perkiraan | beberapa jam |
| Risiko ubahan | rendah |
| Bergantung pada | tidak ada |
| Cabang | `fix/usulan-periode-kosong` |
| Pesan commit | `Izinkan usulan tahunan ketika periode formulir kosong` |

## Mengapa ini penting

Pilihan bawaan formulir operator adalah “Tahunan / tidak berkala” dengan `<option value="">`. `FormData` selalu mengirim `periode=` (string kosong). FastAPI `periode: int | None = Form(None)` menolak `""` sebelum handler jalan, jadi jalur yang didokumentasikan — realisasi tahunan + bukti — tidak pernah membuat usulan.

Belum ada tes HTTP untuk `POST /api/v1/admin/usulan`. `tests/integrasi/test_alur_verifikasi.py` menyisip lewat repository, jadi tidak melihat cacat ini.

## Keadaan sekarang

- `frontend/src/pages/AdminPage.jsx` sekitar baris 298–301:

```jsx
<select name="periode" value={draft.periode} onChange={e=>setDraft({...draft,periode:e.target.value})}>
  <option value="">Tahunan / tidak berkala</option>
  <option value="1">Semester 1</option>
  <option value="2">Semester 2</option>
</select>
```

- `AdminPage.jsx` sekitar 166–174 — kirim `FormData` utuh (termasuk `periode` kosong):

```js
const result=await endpoints.kirimUsulan(new FormData(event.currentTarget))
```

- `backend/app/routers/usulan.py` sekitar 29–62 — `periode: int | None = Form(None)`. Pesan galat “Periode semester harus 1 atau 2”, padahal di service `PERIODE_SAH = (None, 1, 2, 3, 4)`.
- `backend/app/services/verifikasi.py` sekitar 145–149:

```python
PERIODE_SAH = (None, 1, 2, 3, 4)
def periode_sah(periode: int | None) -> bool:
    return periode in PERIODE_SAH
```

- `tests/api/test_kontrak.py` sekitar 385–396 — hanya GET daftar usulan dan tes “admin tidak boleh memutuskan”. Tidak ada POST.
- Benih `tests/api/conftest.py`: akun `admin`, `verifikator.65`, `operator.6501.1`; semua `harus_ganti_password=False`; sandi `SANDI_ADMIN` (`Sebatik-Uji-Kontrak-2026!`). Operator wilayah `6501`. Indikator `ISV-001` sudah `DISETUJUI`. Fixture `auth` hanya admin.
- MIME bukti (`backend/app/services/bukti.py`): `application/pdf`, jpeg, png, xlsx. Tes boleh mengirim isi kecil dengan `content_type="application/pdf"` — tipe diambil dari header, bukan isi berkas.

**Pola yang harus ditiru:** router memvalidasi masukan dan mengubah `Penolakan` jadi `HTTPException`. Penguraian string formulir diletakkan di `services/verifikasi.py` agar router tetap tipis. Impor `Penolakan` dari `backend.app.services` (`services/__init__.py`). Tes HTTP meniru `tests/api/test_keamanan_http.py`.

## Cakupan

**Boleh diubah:**
- `backend/app/services/verifikasi.py` — tambah `baca_periode(...)`.
- `backend/app/routers/usulan.py` — tipe Form `periode` menjadi `str | None`.
- `frontend/src/pages/AdminPage.jsx` — buang `periode` kosong dari FormData.
- `tests/api/test_kontrak.py` — tes HTTP baru.
- `tests/api/conftest.py` — fixture `auth_operator` (session, seperti `auth`).

**Jangan diubah:**
- Alur `putuskan` / larangan verifikasi sendiri.
- Validasi MIME/ukuran unggahan.
- `harus_ganti_password` (itu plan 004).
- Isi `PERIODE_SAH` (jangan buang 3/4).
- Seed indikator / CRUD admin indikator.

## Langkah

### 1. Tulis tes yang gagal

Di `tests/api/conftest.py`, di samping fixture `auth`:

```python
@pytest.fixture(scope="session")
def auth_operator(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "operator.6501.1", "password": SANDI_ADMIN},
    )
    assert response.status_code == 200, "akun operator benih harus dapat masuk"
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
```

`TestClient` sudah diimpor di berkas itu.

Di `tests/api/test_kontrak.py`, tambah `test_operator_kirim_usulan_tahunan_periode_kosong`:

```python
def test_operator_kirim_usulan_tahunan_periode_kosong(client, auth_operator):
    response = client.post(
        "/api/v1/admin/usulan",
        headers=auth_operator,
        data={
            "id_indikator": "ISV-001",
            "tahun": "2024",
            "jenis": "realisasi",
            "nilai": "1.23",
            "periode": "",
            "sumber": "Uji kontrak",
        },
        files={"bukti": ("bukti.pdf", b"%PDF-1.1\n%", "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert {"status", "id", "jumlah_bukti"} == body.keys()
    assert body["status"] == "MENUNGGU_VERIFIKASI"
    assert body["jumlah_bukti"] == 1

    daftar = client.get("/api/v1/admin/usulan", headers=auth_operator).json()["data"]
    baru = next(x for x in daftar if x["id"] == body["id"])
    assert baru["periode"] is None
    assert baru["wilayah_kode"] == "6501"
```

Jangan kirim `wilayah_kode` — operator terkunci ke 6501.

Tes kedua `test_operator_tidak_boleh_usulan_tanpa_bukti`: payload sama tanpa `files` → 422.

**Cek:**

```text
python -m pytest tests/api/test_kontrak.py::test_operator_kirim_usulan_tahunan_periode_kosong -q
```

Harus **GAGAL** (422, bukan 200). Kalau sudah lulus tanpa ubahan produksi, berhenti — bug-nya sudah tidak ada.

### 2. Urai periode di service

Tambah di `backend/app/services/verifikasi.py` (impor `Penolakan` dari `.`):

```python
def baca_periode(mentah: str | int | None) -> int | Penolakan | None:
    """Form HTML mengirim string kosong untuk 'tahunan'; itu bukan angka."""
    if mentah is None or mentah == "":
        return None
    if isinstance(mentah, int):
        nilai = mentah
    else:
        try:
            nilai = int(str(mentah).strip())
        except (TypeError, ValueError):
            return Penolakan(422, "Periode semester harus 1, 2, 3, atau 4")
    if not periode_sah(nilai):
        return Penolakan(422, "Periode semester harus 1, 2, 3, atau 4")
    return nilai
```

Di `routers/usulan.py`:
- Ubah parameter menjadi `periode: str | None = Form(None)`.
- Setelah cek wilayah: `periode_siap = svc_verifikasi.baca_periode(periode)` lalu `if isinstance(periode_siap, Penolakan): raise HTTPException(...)`.
- Hapus `if not svc_verifikasi.periode_sah(periode): raise HTTPException(422, "Periode semester harus 1 atau 2")`.
- Teruskan `periode=periode_siap` ke `ajukan`.

Jangan menambah perulangan di router. Dict respons tetap tiga kunci.

**Cek:** tes langkah 1 lulus.

```text
python -m pytest tests/api/test_kontrak.py tests/integrasi/test_alur_verifikasi.py -q
```

Semua lulus.

### 3. Frontend: buang periode kosong

Di `submitValue` pada `AdminPage.jsx`:

```js
const body=new FormData(event.currentTarget)
if(!body.get('periode')) body.delete('periode')
const result=await endpoints.kirimUsulan(body)
```

Jangan ubah opsi `<select>`.

**Cek:**

```text
cd frontend && pnpm test && pnpm lint
```

Kode keluar 0.

### 4. Lint dan tipe

```text
ruff check backend/app/routers/usulan.py backend/app/services/verifikasi.py tests/api/test_kontrak.py tests/api/conftest.py
mypy backend/app/routers/usulan.py backend/app/services/verifikasi.py
```

Keduanya kode keluar 0.

## Selesai bila semua ini benar

- [ ] `python -m pytest tests/api/test_kontrak.py tests/integrasi/test_alur_verifikasi.py -q` kode keluar 0
- [ ] Tes baru POST `periode=""` → 200 dan `periode` JSON `null`
- [ ] `ruff check` dan `mypy` pada berkas yang disentuh kode keluar 0
- [ ] `cd frontend && pnpm test && pnpm lint` kode keluar 0
- [ ] `git status` tidak menampilkan berkas di luar cakupan
- [ ] Baris 001 di `plans/improve-29-08-2026/README.md` menjadi `DONE`

## Berhenti dan tanya (jangan diteruskan sendiri)

- Tes langkah 1 sudah hijau sebelum kode produksi diubah.
- `periode: int | None = Form(None)` sudah tidak ada dan string kosong sudah diterima.
- Perbaikan seolah membutuhkan ganti versi FastAPI / `python-multipart`.
- Tes unggahan gagal karena MIME — tetap pakai `content_type="application/pdf"`; jangan ubah `bukti.py`.

## Catatan untuk peninjau

Router harus tetap tanpa perulangan, dict respons tetap 3 kunci. Field formulir “kosong = tidak ada” ke depan harus dibuang di klien **dan** diurai sebagai `None` di server.
