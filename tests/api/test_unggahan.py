"""Kontrak endpoint unggah Excel indikator.

Benih `tests/api/conftest.py` hanya berisi 5 indikator sedangkan
`validasi_dataset` mewajibkan tepat 86, jadi tes di sini memakai workbook
sintetis 86 baris. Sebagian besar barisnya karena itu muncul sebagai
`indikator_baru` — itu memang yang diharapkan.

Benih juga sudah memuat satu usulan DISETUJUI untuk ISV-001/2025/realisasi di
wilayah Bulungan; nilai provinsi ISV-001 dipakai untuk menguji perlindungan
konflik dengan menyuntikkan `usulan_id` pada baris provinsi.

Fixture `client`/`db_uji` ber-scope session, jadi tes di berkas ini berjalan
berurutan di atas basis data yang sama.
"""

from __future__ import annotations

import io

import pytest
from openpyxl import Workbook

HEADER_MASTER = [
    "ID Indikator",
    "Kategori",
    "Kelompok / Pilar",
    "Arah Pembangunan",
    "Kode Indikator",
    "Nama Indikator (RPJPD Provinsi / dipakai Kaltara)",
    "Indikator Proxy?",
    "Definisi (RPJPD Provinsi)",
    "Rumus Perhitungan (RPJPD Provinsi)",
    "Interpretasi (RPJPD Provinsi)",
    "Sumber Data (RPJPD Provinsi)",
    "Frekuensi (RPJPD Provinsi)",
    "Status Metadata",
    "Perangkat Daerah Pengampu (Kaltara)",
    "Ketersediaan Data",
    "Periode Data",
    "Tahun Data Terakhir",
]
HEADER_NILAI = [
    "ID Indikator",
    "Kategori",
    "Kelompok / Pilar",
    "Kode Indikator",
    "Nama Indikator (Kaltara)",
    "Jenis Nilai",
    "Tahun",
    "Nilai (Angka)",
    "Nilai (Teks Asli)",
    "Satuan/Catatan",
]


def _id_uji(nomor: int) -> str:
    """10 ISV lalu 76 IUP — mencakup ISV-001/002/005 dan IUP-001/002 dari benih."""
    return f"ISV-{nomor:03d}" if nomor <= 10 else f"IUP-{nomor - 10:03d}"


def _workbook(jumlah: int = 86, nilai: list[list] | None = None) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Basis Data Indikator"
    ws.append(HEADER_MASTER)
    for nomor in range(1, jumlah + 1):
        iid = _id_uji(nomor)
        ws.append(
            [
                iid,
                iid.split("-")[0],
                "Kelompok",
                "Arah",
                str(nomor),
                f"Indikator {iid}",
                "Tidak",
                "Definisi",
                "Rumus",
                "Interpretasi",
                "BPS",
                "Tahunan",
                "Lengkap",
                "BPS",
                "Tersedia",
                "Tahunan",
                2025,
            ]
        )
    ws2 = wb.create_sheet("Data Target-Realisasi")
    ws2.append(HEADER_NILAI)
    for baris in nilai or []:
        ws2.append(baris)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _unggah(client, auth, isi: bytes, nama: str = "uji.xlsx"):
    return client.post(
        "/api/v1/admin/unggah/pratinjau",
        files={"file": (nama, isi, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth,
    )


def test_tanpa_token_ditolak(client):
    assert client.post("/api/v1/admin/unggah/pratinjau").status_code == 403


def test_riwayat_tanpa_token_ditolak(client):
    assert client.get("/api/v1/admin/unggah").status_code == 403


@pytest.mark.parametrize("nama", ["dataset.json", "tabel.csv"])
def test_ekstensi_selain_xlsx_ditolak_422(client, auth, nama):
    response = _unggah(client, auth, b"{}", nama)
    assert response.status_code == 422
    assert "xlsx" in response.json()["detail"].lower()


def test_xls_lama_ditolak_dengan_pesan_khusus(client, auth):
    response = _unggah(client, auth, b"\xd0\xcf\x11\xe0", "lama.xls")
    assert response.status_code == 422
    assert "simpan ulang" in response.json()["detail"].lower()


def test_berkas_teks_berganti_nama_xlsx_ditolak_422_bukan_500(client, auth):
    response = _unggah(client, auth, b"ini teks biasa, bukan zip", "menyamar.xlsx")
    assert response.status_code == 422
    assert response.json()["detail"]


def test_master_kurang_dari_86_ditolak_422(client, auth):
    response = _unggah(client, auth, _workbook(jumlah=85))
    assert response.status_code == 422
    assert "86" in response.json()["detail"]


def test_pratinjau_mengembalikan_diff_dan_ringkasan(client, auth):
    isi = _workbook(
        nilai=[["ISV-003", "ISV", "Kelompok", "3", "Indikator ISV-003", "Realisasi", 2024, 42.0, None, None]]
    )
    response = _unggah(client, auth, isi)
    assert response.status_code == 200, response.text
    body = response.json()

    assert isinstance(body["id"], int)
    diff = body["diff"]
    assert diff["nilai_konflik"] == []
    assert diff["ringkasan"]["indikator"] == 86
    assert diff["ringkasan"]["nilai_dilindungi"] == 0
    # ISV-003 belum ada di benih, jadi harus muncul sebagai indikator baru.
    assert "ISV-003" in diff["indikator_baru"]
    assert any(baris["id"] == "ISV-003" and baris["tahun"] == 2024 for baris in diff["nilai_berubah"])


def test_setuju_memuat_nilai_dan_riwayat_tercatat(client, auth):
    isi = _workbook(
        nilai=[["ISV-004", "ISV", "Kelompok", "4", "Indikator ISV-004", "Realisasi", 2024, 55.5, None, None]]
    )
    pratinjau = _unggah(client, auth, isi)
    unggahan_id = pratinjau.json()["id"]

    setuju = client.post(f"/api/v1/admin/unggah/{unggahan_id}/setujui", headers=auth)
    assert setuju.status_code == 200, setuju.text
    assert setuju.json() == {"status": "DISETUJUI"}

    detail = client.get("/api/v1/admin/indikator/ISV-004", headers=auth)
    assert detail.status_code == 200

    riwayat = client.get("/api/v1/admin/unggah", headers=auth)
    assert riwayat.status_code == 200
    baris = riwayat.json()["data"]
    catatan = next(item for item in baris if item["id"] == unggahan_id)
    # Log mencatat dua waktu: kapan diunggah dan kapan perubahannya diterapkan.
    assert catatan["diunggah_pada"]
    assert catatan["diterapkan_pada"]
    assert catatan["nilai_dimuat"] >= 1
    assert catatan["nilai_dilindungi"] == 0
    assert baris[0]["oleh"] == "admin"


def test_setuju_dua_kali_menghasilkan_404(client, auth):
    isi = _workbook()
    unggahan_id = _unggah(client, auth, isi).json()["id"]
    assert client.post(f"/api/v1/admin/unggah/{unggahan_id}/setujui", headers=auth).status_code == 200
    assert client.post(f"/api/v1/admin/unggah/{unggahan_id}/setujui", headers=auth).status_code == 404


def test_nilai_hasil_verifikasi_dilindungi_dari_unggahan(client, auth, db_uji):
    """Baris ber-`usulan_id` muncul di nilai_konflik dan tidak ikut ditimpa."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from backend.app.models import NilaiIndikator, UsulanNilai

    mesin = create_engine(db_uji)
    pabrik = sessionmaker(bind=mesin)
    with pabrik() as sesi:
        usulan = sesi.query(UsulanNilai).first()
        baris = (
            sesi.query(NilaiIndikator)
            .filter_by(id_indikator="ISV-001", wilayah_kode="65", tahun=2023, jenis="realisasi", periode=None)
            .one()
        )
        baris.usulan_id = usulan.id
        baris.nilai = 777.0
        sesi.commit()
    mesin.dispose()

    isi = _workbook(
        nilai=[["ISV-001", "ISV", "Kelompok", "1", "Indikator ISV-001", "Realisasi", 2023, 1.0, None, None]]
    )
    pratinjau = _unggah(client, auth, isi)
    assert pratinjau.status_code == 200, pratinjau.text
    diff = pratinjau.json()["diff"]

    konflik = diff["nilai_konflik"]
    assert len(konflik) == 1
    assert konflik[0]["id"] == "ISV-001"
    assert konflik[0]["tahun"] == 2023
    assert konflik[0]["lama"] == 777.0
    assert konflik[0]["baru"] == 1.0
    assert konflik[0]["usulan_id"] is not None
    assert diff["ringkasan"]["nilai_dilindungi"] == 1
    # Baris konflik tidak boleh ikut muncul di daftar yang akan dimuat.
    # `jenis` ikut dicocokkan: baris target ISV-001/2023 memang berubah dan
    # bukan konflik, jadi tanpa itu asersi ini salah sasaran.
    assert not any(
        b["id"] == "ISV-001" and b["tahun"] == 2023 and b["jenis"] == "realisasi" for b in diff["nilai_berubah"]
    )

    setuju = client.post(f"/api/v1/admin/unggah/{pratinjau.json()['id']}/setujui", headers=auth)
    assert setuju.status_code == 200, setuju.text

    mesin = create_engine(db_uji)
    pabrik = sessionmaker(bind=mesin)
    with pabrik() as sesi:
        tetap = (
            sesi.query(NilaiIndikator)
            .filter_by(id_indikator="ISV-001", wilayah_kode="65", tahun=2023, jenis="realisasi", periode=None)
            .one()
        )
        assert tetap.nilai == 777.0, "nilai hasil verifikasi tidak boleh ditimpa unggahan"
    mesin.dispose()


def test_riwayat_unggahan_belum_disetujui_tanpa_waktu_penerapan(client, auth):
    """Baris yang baru dipratinjau tercatat waktunya, tapi belum punya hasil."""
    unggahan_id = _unggah(client, auth, _workbook(), "belum-disetujui.xlsx").json()["id"]

    catatan = next(
        item for item in client.get("/api/v1/admin/unggah", headers=auth).json()["data"] if item["id"] == unggahan_id
    )
    assert catatan["diunggah_pada"]
    assert catatan["diterapkan_pada"] is None
    assert catatan["nilai_dimuat"] is None
