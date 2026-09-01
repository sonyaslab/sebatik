"""Perhitungan kelengkapan slot data pada empat lapis klasifikasi."""

from __future__ import annotations

from typing import NamedTuple

from sqlalchemy.orm import Session

from ..repositories import indikator as repo_indikator
from ..repositories import nilai as repo_nilai

# Rentang tahun realisasi yang dihitung sebagai "slot" ketersediaan.
TAHUN_AWAL = 2021
TAHUN_AKHIR = 2025
JUMLAH_SLOT_PER_INDIKATOR = TAHUN_AKHIR - TAHUN_AWAL + 1

# (kolom klasifikasi, label tampil, jumlah kelompok menurut dokumen RPJPD).
DIMENSI: tuple[tuple[str, str, int], ...] = (
    ("sasaran_visi", "Sasaran Visi", 5),
    ("misi_agenda", "Misi/Agenda Pembangunan", 8),
    ("arah_ie", "Arah Pembangunan", 17),
    ("indikator_induk", "Indikator Utama Pembangunan", 45),
)


class Kelompok(NamedTuple):
    kode: str
    label: str
    jumlah_kelompok: int
    jumlah_indikator: int
    slot_terisi: int
    slot_total: int
    persentase: float


def _persentase(terisi: int, total: int) -> float:
    return round(terisi / total * 100, 1) if total else 0


def ketersediaan_tahunan(session: Session, tahun_tersedia: list[int], wilayah_kode: str) -> list[dict[str, object]]:
    """Ketersediaan realisasi per tahun untuk seluruh indikator, ISV, dan IUP."""
    indikator = repo_indikator.daftar_terverifikasi(session)
    menurut_kategori = {
        kategori: [item.id_indikator for item in indikator if item.kategori == kategori] for kategori in ("ISV", "IUP")
    }
    semua = [item.id_indikator for item in indikator]
    hasil = []
    for tahun in tahun_tersedia:
        terisi = repo_nilai.hitung_terisi_tahun(session, semua, wilayah_kode, tahun)
        rincian = {}
        for kategori, daftar_id in menurut_kategori.items():
            jumlah = repo_nilai.hitung_terisi_tahun(session, daftar_id, wilayah_kode, tahun)
            rincian[kategori.lower()] = {
                "terisi": jumlah,
                "total": len(daftar_id),
                "persentase": _persentase(jumlah, len(daftar_id)),
            }
        hasil.append(
            {
                "tahun": tahun,
                "terisi": terisi,
                "total": len(semua),
                "persentase": _persentase(terisi, len(semua)),
                **rincian,
            }
        )
    return hasil


def ketersediaan_kelompok(session: Session) -> list[dict[str, object]]:
    """Daftar kelompok unik pada setiap dimensi kerangka pembangunan."""
    hasil = []
    for kolom, label, jumlah_kelompok in DIMENSI:
        daftar = repo_indikator.daftar_berklasifikasi(session, kolom)
        id_indikator = [item.id_indikator for item in daftar]
        terisi = repo_nilai.hitung_slot_terisi(session, id_indikator, TAHUN_AWAL, TAHUN_AKHIR)
        total = len(id_indikator) * JUMLAH_SLOT_PER_INDIKATOR
        hasil.append(
            Kelompok(
                kode=kolom,
                label=label,
                jumlah_kelompok=jumlah_kelompok,
                jumlah_indikator=len(id_indikator),
                slot_terisi=terisi,
                slot_total=total,
                persentase=_persentase(terisi, total),
            )._asdict()
            | {"kelompok": _kelompok_dimensi(daftar, kolom)}
        )
    return hasil


def _kelompok_dimensi(daftar: list, kolom: str) -> list[dict[str, object]]:
    """Nama klasifikasi unik beserta banyak indikator yang menjadi anggotanya."""
    hasil = []
    for nama_asli in dict.fromkeys(getattr(item, kolom) for item in daftar):
        anggota = [item for item in daftar if getattr(item, kolom) == nama_asli]
        hasil.append(
            {
                "nama": nama_asli,
                "jumlah_indikator": len(anggota),
                "id_indikator": [item.id_indikator for item in anggota],
            }
        )
    return hasil
