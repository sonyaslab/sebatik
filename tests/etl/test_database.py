"""Kontrak dataset database sebagai satu-satunya masukan loader produksi."""

from __future__ import annotations

import copy

import pytest

from backend.app.models import Indikator, MetadataIndikator, NilaiIndikator
from src.etl.database import DatasetTidakValid, muat_dataset, transformasi_sumber_database, validasi_dataset


def sumber_database() -> dict:
    kepala_master = [
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
    master = [kepala_master]
    for nomor in range(1, 87):
        kategori = "ISV" if nomor <= 6 else "IUP"
        master.append(
            [
                f"{kategori}-{nomor:03d}",
                kategori,
                "Kelompok",
                "Arah",
                str(nomor),
                f"Indikator {nomor}",
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
    nilai = [
        [
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
    ]
    nilai.append(["ISV-001", "ISV", "Kelompok", "1", "Indikator 1", "Realisasi", 2025, 10.5, None, None])
    return {"source": "master.json", "sheets": {"Basis Data Indikator": master, "Data Target-Realisasi": nilai}}


def test_transformasi_menghasilkan_master_tiga_digit_dan_manifest():
    dataset = transformasi_sumber_database(sumber_database())
    assert dataset["manifest"] == {"indikator": 86, "metadata_indikator": 86, "nilai_indikator": 1}
    assert dataset["data"]["indikator"][0]["id_indikator"] == "ISV-001"
    assert dataset["data"]["nilai_indikator"][0]["wilayah_kode"] == "65"


def test_checksum_mendeteksi_perubahan_setelah_transformasi():
    dataset = transformasi_sumber_database(sumber_database())
    rusak = copy.deepcopy(dataset)
    rusak["data"]["nilai_indikator"][0]["nilai"] = 99
    with pytest.raises(DatasetTidakValid, match="Checksum"):
        validasi_dataset(rusak)


def test_loader_mengisi_database_kosong(session):
    dataset = transformasi_sumber_database(sumber_database())
    hasil = muat_dataset(session, dataset)
    session.flush()
    assert hasil == {"indikator": 86, "metadata_indikator": 86, "nilai_indikator": 1, "nilai_dilewati": 0}
    assert session.query(Indikator).count() == 86
    assert session.query(MetadataIndikator).count() == 86
    assert session.query(NilaiIndikator).one().nilai == 10.5


def test_loader_melewati_nilai_yang_dilindungi(session):
    """`lewati_nilai` melindungi baris hasil verifikasi dari ditimpa unggahan."""
    dataset = transformasi_sumber_database(sumber_database())
    hasil = muat_dataset(session, dataset, lewati_nilai={("ISV-001", "65", 2025, "realisasi", None)})
    session.flush()

    assert hasil["nilai_indikator"] == 0
    assert hasil["nilai_dilewati"] == 1
    assert session.query(NilaiIndikator).count() == 0
    # Dimensi tetap dimuat penuh; yang dilindungi hanya tabel fakta.
    assert session.query(Indikator).count() == 86


def test_loader_tanpa_lewati_nilai_berperilaku_seperti_semula(session):
    dataset = transformasi_sumber_database(sumber_database())
    hasil = muat_dataset(session, dataset, lewati_nilai=set())
    session.flush()

    assert hasil["nilai_indikator"] == 1
    assert hasil["nilai_dilewati"] == 0
    assert session.query(NilaiIndikator).one().nilai == 10.5


def test_loader_tidak_menimpa_nilai_lama_yang_dilindungi(session):
    """Baris yang sudah ada dan dilindungi harus tetap memakai angka lamanya."""
    from backend.app.repositories import nilai as repo_nilai

    muat_dataset(session, transformasi_sumber_database(sumber_database()))
    session.flush()
    repo_nilai.upsert(session, id_indikator="ISV-001", wilayah_kode="65", tahun=2025, jenis="realisasi", nilai=99.9)
    session.flush()

    muat_dataset(
        session,
        transformasi_sumber_database(sumber_database()),
        lewati_nilai={("ISV-001", "65", 2025, "realisasi", None)},
    )
    session.flush()

    assert session.query(NilaiIndikator).one().nilai == 99.9
