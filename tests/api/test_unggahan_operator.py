"""Kontrak unggahan realisasi massal untuk operator wilayah."""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.models import NilaiIndikator, StatusVerifikasi

SANDI = "Sebatik-Uji-Kontrak-2026!"
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _workbook(*baris: list[object], sheet: str = "6501") -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(
        [
            "wilayah_kode",
            "id_indikator",
            "nama_indikator",
            "tahun",
            "jenis",
            "periode",
            "nilai",
            "nilai_teks",
            "sumber",
            "catatan",
        ]
    )
    for item in baris:
        ws.append(item)
    stream = BytesIO()
    wb.save(stream)
    return stream.getvalue()


def _auth_verifikator(client) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", data={"username": "verifikator.65", "password": SANDI})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_template_hanya_dapat_diunduh_operator(client, auth, auth_operator):
    assert client.get("/api/v1/operator/unggah-template", headers=auth).status_code == 403
    response = client.get("/api/v1/operator/unggah-template", headers=auth_operator)
    assert response.status_code == 200
    assert response.content.startswith(b"PK")


def test_operator_unggah_batch_angka_dan_teks_lalu_verifikator_setujui(client, auth_operator, db_uji):
    isi = _workbook(
        ["6501", "ISV-003", "Indikator angka", 2024, "realisasi", None, "7,30", None, "BPS", None],
        ["6501", "ISV-004", "Indikator teks", 2024, "realisasi", None, None, "Sedang", "OPD", "uji"],
    )
    unggah = client.post(
        "/api/v1/operator/unggah",
        headers=auth_operator,
        files={"berkas": ("realisasi.xlsx", isi, MIME_XLSX)},
    )
    assert unggah.status_code == 200, unggah.text
    hasil = unggah.json()
    assert hasil["jumlah_usulan"] == 2
    assert hasil["jumlah_angka"] == 1
    assert hasil["jumlah_teks"] == 1

    keputusan = client.post(
        f"/api/v1/admin/usulan/batch/{hasil['batch_id']}/verifikasi",
        headers=_auth_verifikator(client),
        data={"keputusan": StatusVerifikasi.DISETUJUI},
    )
    assert keputusan.status_code == 200, keputusan.text
    assert keputusan.json()["jumlah_usulan"] == 2

    mesin = create_engine(db_uji)
    with Session(mesin) as session:
        angka = session.scalar(
            select(NilaiIndikator).where(
                NilaiIndikator.id_indikator == "ISV-003",
                NilaiIndikator.wilayah_kode == "6501",
                NilaiIndikator.tahun == 2024,
            )
        )
        teks = session.scalar(
            select(NilaiIndikator).where(
                NilaiIndikator.id_indikator == "ISV-004",
                NilaiIndikator.wilayah_kode == "6501",
                NilaiIndikator.tahun == 2024,
            )
        )
        assert angka.nilai == 7.3
        assert teks.nilai is None
        assert teks.nilai_teks == "Sedang"
    mesin.dispose()


def test_operator_tidak_dapat_mengunggah_wilayah_lain_atau_target(client, auth_operator):
    wilayah_lain = _workbook(
        ["6502", "ISV-003", "Salah wilayah", 2025, "realisasi", None, 1, None, "BPS", None]
    )
    response = client.post(
        "/api/v1/operator/unggah",
        headers=auth_operator,
        files={"berkas": ("salah.xlsx", wilayah_lain, MIME_XLSX)},
    )
    assert response.status_code == 403

    target = _workbook(
        ["6501", "ISV-003", "Target", 2025, "target", None, 1, None, "BPS", None]
    )
    response = client.post(
        "/api/v1/operator/unggah",
        headers=auth_operator,
        files={"berkas": ("target.xlsx", target, MIME_XLSX)},
    )
    assert response.status_code == 403
