"""Kontrak pemetaan empat lapis kerangka pembangunan."""

from __future__ import annotations

from src.etl.klasifikasi import klasifikasi_kerangka, nama_indikator_utama


def test_isv_menggunakan_arah_sebagai_sasaran_visi():
    hasil = klasifikasi_kerangka(
        {
            "Kategori": "ISV",
            "Kelompok / Pilar": "Sasaran Visi Indonesia Emas 2045",
            "Arah Pembangunan": "Peningkatan Pendapatan per Kapita",
            "Kode Indikator": "1",
        }
    )
    assert hasil == {
        "sasaran_visi": "Peningkatan Pendapatan per Kapita",
        "misi_agenda": None,
        "arah_ie": None,
        "indikator_induk": None,
    }


def test_iup_menghasilkan_misi_arah_dan_indikator_induk():
    hasil = klasifikasi_kerangka(
        {
            "Kategori": "IUP",
            "Kelompok / Pilar": "Transformasi Sosial",
            "Arah Pembangunan": "IE2 - Pendidikan Berkualitas yang Merata",
            "Kode Indikator": "5.a.1",
        }
    )
    assert hasil == {
        "sasaran_visi": None,
        "misi_agenda": "Transformasi Sosial",
        "arah_ie": "Pendidikan Berkualitas yang Merata",
        "indikator_induk": "Hasil Pembelajaran",
    }


def test_kolom_eksplisit_diutamakan_dari_hasil_turunan():
    hasil = klasifikasi_kerangka(
        {
            "Kategori": "IUP",
            "Kelompok / Pilar": "Kelompok lama",
            "Arah Pembangunan": "IE1 - Arah lama",
            "Kode Indikator": "1",
            "Misi/Agenda Pembangunan": "Misi terverifikasi",
            "Arah IE": "IE9 - Arah terverifikasi",
            "Indikator Utama Pembangunan": "Induk terverifikasi",
        }
    )
    assert hasil["misi_agenda"] == "Misi terverifikasi"
    assert hasil["arah_ie"] == "Arah terverifikasi"
    assert hasil["indikator_induk"] == "Induk terverifikasi"


def test_kode_turunan_dikelompokkan_ke_nomor_utama():
    assert nama_indikator_utama("42.c-ii") == "Kualitas Lingkungan Hidup"
    assert nama_indikator_utama("45.b") == "Persentase Penurunan Emisi GRK"
