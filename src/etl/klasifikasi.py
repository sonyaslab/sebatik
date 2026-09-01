"""Pemetaan empat lapis kerangka pembangunan dari workbook master.

Workbook lama hanya menyediakan ``Kelompok / Pilar``, ``Arah Pembangunan``,
dan ``Kode Indikator``. Workbook baru boleh menyediakan empat kolom eksplisit;
fungsi ini tetap menerima bentuk lama agar unggahan terdahulu tidak langsung
ditolak, tetapi selalu menghasilkan bentuk database yang sama.
"""

from __future__ import annotations

import re
from typing import Any

NAMA_INDIKATOR_UTAMA: tuple[str, ...] = (
    "Usia Harapan Hidup",
    "Kesehatan Ibu dan Anak",
    "Penanganan Tuberkulosis",
    "Cakupan Kepesertaan Jaminan Kesehatan Nasional",
    "Hasil Pembelajaran",
    "Rata-rata Lama Sekolah",
    "Harapan Lama Sekolah",
    "Proporsi Penduduk Berkualifikasi Pendidikan Tinggi",
    "Pekerja Lulusan Pendidikan Menengah dan Tinggi di Bidang Keahlian Menengah Tinggi",
    "Tingkat Kemiskinan",
    "Cakupan Kepesertaan Jaminan Sosial Ketenagakerjaan",
    "Penyandang Disabilitas Bekerja di Sektor Formal",
    "Produktivitas Industri dan Pertanian",
    "Pembentukan Modal Tetap Bruto",
    "Tingkat Pengangguran Terbuka",
    "Tingkat Partisipasi Angkatan Kerja Perempuan",
    "Kontribusi Pariwisata terhadap PDRB",
    "Kontribusi Ekonomi Kreatif terhadap PDRB",
    "Produktivitas Perkotaan",
    "Biaya Logistik",
    "Pembentukan Modal Tetap Bruto terhadap PDRB",
    "Ekspor Barang dan Jasa",
    "Kota dan Desa Maju, Inklusif, dan Berkelanjutan",
    "Indeks Reformasi Hukum",
    "Indeks Sistem Pemerintahan Berbasis Elektronik",
    "Indeks Pelayanan Publik",
    "Indeks Integritas Nasional",
    "Indeks Pembangunan Hukum",
    "Rasa Aman di Lingkungan Tempat Tinggal",
    "Indeks Demokrasi Indonesia",
    "Rasio Pajak Daerah terhadap PDRB",
    "Tingkat Inflasi",
    "Pendalaman dan Intermediasi Sektor Keuangan",
    "Inklusi Keuangan",
    "Ketangguhan Diplomasi",
    "Ketangguhan Pertahanan",
    "Indeks Pembangunan Kebudayaan",
    "Indeks Kerukunan Umat Beragama",
    "Indeks Pembangunan Kualitas Keluarga",
    "Indeks Ketimpangan Gender",
    "Indeks Pengelolaan Keanekaragaman Hayati",
    "Kualitas Lingkungan Hidup",
    "Ketahanan Energi, Air, dan Pangan",
    "Indeks Risiko Bencana",
    "Persentase Penurunan Emisi GRK",
)

POLA_ARAH_IE = re.compile(r"^IE\s*\d+\s*[-–—:]\s*", re.IGNORECASE)
POLA_NOMOR_INDUK = re.compile(r"^(\d+)")


def _teks(nilai: Any) -> str | None:
    if nilai is None:
        return None
    hasil = re.sub(r"\s+", " ", str(nilai)).strip()
    return hasil or None


def nama_arah_ie(nilai: Any) -> str | None:
    """Hilangkan prefiks ``IE1 -`` karena kode bukan bagian nama tampil."""
    teks = _teks(nilai)
    return POLA_ARAH_IE.sub("", teks).strip() if teks else None


def nama_indikator_utama(kode: Any) -> str | None:
    """Kelompokkan kode turunan, mis. ``5.a.1``, ke indikator induk 5."""
    cocok = POLA_NOMOR_INDUK.match(_teks(kode) or "")
    if not cocok:
        return None
    nomor = int(cocok.group(1))
    return NAMA_INDIKATOR_UTAMA[nomor - 1] if 1 <= nomor <= len(NAMA_INDIKATOR_UTAMA) else None


def klasifikasi_kerangka(baris: dict[str, Any]) -> dict[str, str | None]:
    """Kembalikan empat field klasifikasi; kolom eksplisit selalu diutamakan."""
    kategori = (_teks(baris.get("Kategori")) or "").upper()
    kelompok = _teks(baris.get("Kelompok / Pilar"))
    arah = _teks(baris.get("Arah Pembangunan"))

    sasaran_visi = _teks(baris.get("Sasaran Visi"))
    misi_agenda = _teks(baris.get("Misi/Agenda Pembangunan"))
    arah_ie = nama_arah_ie(baris.get("Arah IE"))
    indikator_induk = _teks(baris.get("Indikator Utama Pembangunan"))

    if kategori == "ISV":
        sasaran_visi = sasaran_visi or arah
    elif kategori == "IUP":
        misi_agenda = misi_agenda or kelompok
        arah_ie = arah_ie or nama_arah_ie(arah)
        indikator_induk = indikator_induk or nama_indikator_utama(baris.get("Kode Indikator"))

    return {
        "sasaran_visi": sasaran_visi,
        "misi_agenda": misi_agenda,
        "arah_ie": arah_ie,
        "indikator_induk": indikator_induk,
    }
