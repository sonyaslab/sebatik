"""Skema unggahan Excel massal."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class NilaiBerubah(BaseModel):
    id: str
    tahun: int
    jenis: str
    lama: float | None = None
    baru: float | None = None


class NilaiKonflik(NilaiBerubah):
    """Baris yang TIDAK akan ditimpa karena berasal dari alur verifikasi."""

    usulan_id: int | None = None


class RingkasanUnggahan(BaseModel):
    indikator: int
    nilai_dimuat: int
    nilai_dilindungi: int


class DiffUnggahan(BaseModel):
    indikator_baru: list[str]
    indikator_hilang: list[str]
    nilai_berubah: list[NilaiBerubah]
    nilai_konflik: list[NilaiKonflik]
    ringkasan: RingkasanUnggahan


class PratinjauResponse(BaseModel):
    id: int
    diff: DiffUnggahan


class RiwayatUnggahan(BaseModel):
    """Satu baris log unggahan: kapan diunggah, kapan perubahannya diterapkan."""

    id: int
    nama_file_asli: str
    status: str
    diunggah_pada: datetime | None = None
    diterapkan_pada: datetime | None = None
    nilai_dimuat: int | None = None
    nilai_dilindungi: int | None = None
    indikator_baru: int | None = None
    oleh: str | None = None


class RiwayatUnggahanResponse(BaseModel):
    data: list[RiwayatUnggahan]
