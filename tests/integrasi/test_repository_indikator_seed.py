"""Tes repository.indikator: hitung baris dan insert massal untuk seed."""

from __future__ import annotations

from backend.app.repositories import indikator as repo_indikator


def test_jumlah_nol_saat_tabel_kosong(session):
    assert repo_indikator.jumlah(session) == 0


def test_jumlah_menghitung_baris_yang_ada(session):
    from backend.app.models import Indikator

    session.add(Indikator(id_indikator="ISV-001", kategori="ISV", nomor=1, nama_indikator="Contoh"))
    session.flush()

    assert repo_indikator.jumlah(session) == 1


def test_seed_massal_insert_ke_tiga_tabel(session):
    from backend.app.models import Indikator, MetadataIndikator, NilaiIndikator

    repo_indikator.seed_massal(
        session,
        indikator=[{"id_indikator": "ISV-001", "kategori": "ISV", "nomor": 1, "nama_indikator": "Contoh"}],
        metadata=[{"id_indikator": "ISV-001", "definisi": "Definisi contoh"}],
        nilai=[
            {
                "id_indikator": "ISV-001",
                "wilayah_kode": "65",
                "tahun": 2021,
                "jenis": "realisasi",
                "nilai": 100.0,
            }
        ],
    )
    session.flush()

    assert session.get(Indikator, "ISV-001") is not None
    assert session.get(MetadataIndikator, "ISV-001").definisi == "Definisi contoh"
    baris_nilai = session.query(NilaiIndikator).filter_by(id_indikator="ISV-001").one()
    assert baris_nilai.tahun == 2021
    assert baris_nilai.jenis == "realisasi"
