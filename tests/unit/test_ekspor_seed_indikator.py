"""Tes fungsi pembacaan Excel klasifikasi -> dict siap-seed.

Memakai workbook in-memory (bukan file di disk) supaya cepat dan tidak
bergantung pada data/raw/ yang tidak ter-commit.
"""

from __future__ import annotations

import pytest
from openpyxl import Workbook

from scripts.ekspor_seed_indikator import (
    baca_indikator_dan_metadata,
    baca_nilai,
    indeks_kanonis,
)

HEADER_INDIKATOR = [
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
    "Catatan Kualitas Data",
    "Keterangan (Rakor Kaltara)",
    "Keterangan RPJMD / Catatan Kaltara",
    "Kelompok Makro",
]


def _wb_indikator(baris: list[list]) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Basis Data Indikator"
    ws.append(HEADER_INDIKATOR)
    for satu in baris:
        ws.append(satu)
    return wb


def test_arah_pembangunan_untuk_isv_arah_ie_untuk_iup():
    wb = _wb_indikator(
        [
            [
                "ISV-001",
                "ISV",
                "Sasaran Visi",
                "Peningkatan Pendapatan per Kapita",
                "1",
                "PDRB per Kapita",
                "Tidak",
                "def isv",
                "rumus isv",
                "interp isv",
                "BPS",
                "Tahunan",
                "Lengkap",
                "BPS",
                "Tersedia",
                "Tahunan",
                2025,
                None,
                None,
                None,
            ],
            [
                "IUP-001",
                "IUP",
                "Transformasi Sosial",
                "IE1 - Kesehatan untuk Semua",
                "1",
                "Usia Harapan Hidup",
                "Tidak",
                "def iup",
                "rumus iup",
                "interp iup",
                "BPS",
                "Tahunan",
                "Lengkap",
                "Dinkes",
                "Tersedia",
                "Tahunan",
                2025,
                None,
                None,
                None,
            ],
        ]
    )

    indikator, _metadata = baca_indikator_dan_metadata(wb)
    isv = next(i for i in indikator if i["id_indikator"] == "ISV-001")
    iup = next(i for i in indikator if i["id_indikator"] == "IUP-001")

    assert isv["arah_pembangunan"] == "Peningkatan Pendapatan per Kapita"
    assert isv["arah_ie"] is None
    assert iup["arah_ie"] == "IE1 - Kesehatan untuk Semua"
    assert iup["arah_pembangunan"] is None


def test_nomor_diturunkan_dari_suffix_id():
    wb = _wb_indikator(
        [
            [
                "ISV-087",
                "ISV",
                "Sasaran Visi",
                "Arah",
                "87",
                "Nama",
                "Tidak",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ]
        ]
    )
    indikator, _metadata = baca_indikator_dan_metadata(wb)
    assert indikator[0]["nomor"] == 87
    assert indikator[0]["kode_indikator"] == "87"


def test_kelompok_makro_dibaca_dari_master():
    wb = _wb_indikator(
        [
            [
                "ISV-001",
                "ISV",
                "Kelompok",
                "Arah",
                "1",
                "Nama",
                "Tidak",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "Makro - Ekonomi",
            ]
        ]
    )
    indikator, _metadata = baca_indikator_dan_metadata(wb)
    assert indikator[0]["kelompok_makro"] == "Makro - Ekonomi"


def test_catatan_tiga_kolom_digabung_dengan_prefiks_dan_kolom_kosong_dilewati():
    wb = _wb_indikator(
        [
            [
                "ISV-001",
                "ISV",
                "Kelompok",
                "Arah",
                "1",
                "Nama",
                "Tidak",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                "Catatan A",
                None,
                "Catatan C",
            ]
        ]
    )
    indikator, _metadata = baca_indikator_dan_metadata(wb)
    assert indikator[0]["catatan_teknis"] == (
        "[Catatan Kualitas Data] Catatan A\n[Keterangan RPJMD / Catatan Kaltara] Catatan C"
    )


def test_metadata_ikut_terisi_dari_kolom_definisi_rumus_interpretasi():
    wb = _wb_indikator(
        [
            [
                "ISV-001",
                "ISV",
                "Kelompok",
                "Arah",
                "1",
                "Nama",
                "Tidak",
                "Definisi X",
                "Rumus X",
                "Interpretasi X",
                "Sumber X",
                "Tahunan",
                "Lengkap",
                "OPD X",
                "Tersedia",
                "Tahunan",
                2025,
                None,
                None,
                None,
            ]
        ]
    )
    _indikator, metadata = baca_indikator_dan_metadata(wb)
    assert metadata[0] == {
        "id_indikator": "ISV-001",
        "definisi": "Definisi X",
        "rumus_mentah": "Rumus X",
        "interpretasi": "Interpretasi X",
        "sumber_data": "Sumber X",
        "frekuensi": "Tahunan",
        "status_metadata": "Lengkap",
    }


def test_baris_tanpa_id_indikator_dilewati():
    wb = _wb_indikator([[None] * 20])
    indikator, metadata = baca_indikator_dan_metadata(wb)
    assert indikator == []
    assert metadata == []


def _wb_nilai(baris: list[list]) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "Data Target-Realisasi"
    ws.append(
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
    )
    for satu in baris:
        ws.append(satu)
    return wb


def test_baca_nilai_memetakan_jenis_dan_wilayah_provinsi():
    wb = _wb_nilai(
        [
            ["ISV-001", "ISV", "Kelompok", "1", "Nama", "Realisasi", 2021, 157.09, None, None],
            ["ISV-001", "ISV", "Kelompok", "1", "Nama", "Target", 2025, 227.1, None, None],
        ]
    )
    nilai = baca_nilai(wb, {("ISV", "1"): "ISV-001"})
    assert len(nilai) == 2
    assert nilai[0]["jenis"] == "realisasi"
    assert nilai[0]["wilayah_kode"] == "65"
    assert nilai[0]["periode"] is None
    assert nilai[0]["tahun"] == 2021
    assert nilai[0]["nilai"] == 157.09
    assert nilai[1]["jenis"] == "target"


def test_baca_nilai_melewati_baris_jenis_tidak_dikenal():
    wb = _wb_nilai([["ISV-001", "ISV", "Kelompok", "1", "Nama", "Bukan Jenis", 2021, 1.0, None, None]])
    assert baca_nilai(wb, {("ISV", "1"): "ISV-001"}) == []


def test_baca_nilai_mempertahankan_teks_asli_dan_satuan_catatan():
    wb = _wb_nilai([["IUP-001", "IUP", "Kelompok", "1", "Nama", "Realisasi", 2020, None, "70,5", "angka sementara"]])
    nilai = baca_nilai(wb, {("IUP", "1"): "IUP-001"})
    assert nilai[0]["nilai"] is None
    assert nilai[0]["nilai_teks"] == "70,5"
    assert nilai[0]["satuan_catatan"] == "angka sementara"


def test_indeks_kanonis_memetakan_kategori_dan_kode_ke_id():
    wb = _wb_indikator(
        [
            [
                "ISV-001",
                "ISV",
                "Kelompok",
                "Arah",
                "1",
                "Nama",
                "Tidak",
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ]
        ]
    )
    indikator, _metadata = baca_indikator_dan_metadata(wb)
    assert indeks_kanonis(indikator) == {("ISV", "1"): "ISV-001"}


def test_baca_nilai_memakai_kode_bukan_id_indikator_sheet_nilai():
    """Penomoran IUP kedua sheet berbeda; kunci gabung wajib (kategori, kode).

    Baris di bawah memakai ID "IUP-011" seperti di sheet nilai asli, padahal
    indikator yang dimaksud (kode "1") adalah "IUP-001" di sheet pertama.
    """
    wb = _wb_nilai([["IUP-011", "IUP", "Kelompok", "1", "Nama", "Realisasi", 2021, 70.5, None, None]])
    nilai = baca_nilai(wb, {("IUP", "1"): "IUP-001"})
    assert nilai[0]["id_indikator"] == "IUP-001"


def test_baca_nilai_gagal_keras_saat_kode_tidak_dikenal():
    wb = _wb_nilai([["IUP-011", "IUP", "Kelompok", "99", "Nama", "Realisasi", 2021, 1.0, None, None]])
    with pytest.raises(ValueError, match="tidak ada di sheet"):
        baca_nilai(wb, {("IUP", "1"): "IUP-001"})
