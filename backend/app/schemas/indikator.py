"""Skema daftar indikator, detail, dan metadata."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator

from .capaian import MuatanCapaian


def _kosong_jadi_none(nilai: Any) -> Any:
    """Isian yang dikosongkan di form terkirim sebagai "", bukan sebagai absen.

    Tanpa ini, membiarkan kolom angka opsional kosong — kasus yang paling
    lazim — membuat Pydantic menolak seluruh form dengan 422 int_parsing.
    """
    if isinstance(nilai, str) and nilai.strip() == "":
        return None
    return nilai


# Kolom angka opsional pada form admin: "" dari form berarti "kosongkan".
OpsionalInt = Annotated[int | None, BeforeValidator(_kosong_jadi_none)]


class IndikatorPublik(BaseModel):
    """Kolom yang boleh keluar lewat daftar publik.

    `opd_penanggung_jawab` adalah nama lama `opd_pengampu` yang dipertahankan
    demi kontrak; lihat `services/indikator.NAMA_LAMA`.
    """

    id_indikator: str
    nama_indikator: str | None = None
    kategori: str | None = None
    kelompok: str | None = None
    satuan: str | None = None
    tim_pjk: str | None = None
    opd_penanggung_jawab: str | None = None
    status_metadata: str | None = None
    tahun_terakhir: int | None = None
    is_proxy: bool | None = None


class DaftarIndikatorResponse(BaseModel):
    data: list[IndikatorPublik]
    total: int
    page: int
    page_size: int


class NilaiRingkas(BaseModel):
    tahun: int
    jenis: str
    nilai: float | None = None
    # Nama lama `sumber_sheet` dipertahankan demi kontrak frontend.
    sumber_sheet: str | None = None


class MetadataTeknis(BaseModel):
    definisi: str | None = None
    rumus_mentah: str | None = None
    interpretasi: str | None = None
    sumber_data: str | None = None
    frekuensi: str | None = None
    halaman_sumber: str | None = None
    sumber_metadata: str | None = None
    perlu_verifikasi_manual: bool | None = None


class DetailIndikatorResponse(MuatanCapaian):
    nilai: list[NilaiRingkas]
    metadata: MetadataTeknis | None = None


class MetadataMaster(BaseModel):
    definisi: str | None = None
    rumus_mentah: str | None = None
    rumus_latex: str | None = None
    # Keterangan notasi rumus: daftar "simbol = arti" yang di Buku 1 tercetak
    # persis di bawah rumusnya. Disimpan satu baris per notasi.
    keterangan_rumus: list[str] = []
    perlu_verifikasi_rumus: bool = False
    halaman_sumber: str | None = None
    interpretasi: str | None = None
    sumber_data: str | None = None
    frekuensi: str | None = None
    status_metadata: str | None = None
    sumber_metadata: str | None = None


class NilaiMaster(BaseModel):
    tahun: int
    jenis: str
    nilai: float | None = None
    nilai_teks: str | None = None
    satuan_catatan: str | None = None


class MetadataResponse(BaseModel):
    id_indikator: str
    kategori: str | None = None
    kode_indikator: str | None = None
    nama_indikator: str | None = None
    kelompok: str | None = None
    arah_pembangunan: str | None = None
    satuan: str | None = None
    opd_pengampu: str | None = None
    status_ketersediaan: str | None = None
    periode_data: str | None = None
    metadata: MetadataMaster | None = None
    metadata_tersedia: bool
    nilai: list[NilaiMaster]


class ArahBaikResponse(BaseModel):
    status: str
    id_indikator: str
    arah_baik: str


class IndikatorFormDasar(BaseModel):
    """Field yang bisa diisi/diedit admin lewat form CRUD.

    Dipakai dua kali: `IndikatorFormBuat` (create, + id_indikator) dan
    langsung sebagai body `PUT` (update, id_indikator datang dari path,
    bukan dari sini — lihat backend/app/routers/admin.py).

    `kategori`+`nomor` tetap wajib diisi bahkan saat update, supaya
    services.indikator.periksa_konsistensi_id bisa memvalidasi keduanya
    tetap cocok dengan id_indikator yang sudah ada (id_indikator sendiri
    tidak pernah bisa diubah setelah dibuat — itu primary key).
    """

    kategori: str
    nomor: int
    nama_indikator: str
    kode_indikator: str | None = None
    nama_asli: str | None = None
    kelompok: str | None = None
    arah_pembangunan: str | None = None
    sasaran_visi: str | None = None
    misi_agenda: str | None = None
    arah_ie: str | None = None
    indikator_induk: str | None = None
    kelompok_makro: str | None = None
    satuan: str | None = None
    penghasil: str | None = None
    kl_pengampu: str | None = None
    opd_pengampu: str | None = None
    tim_pjk: str | None = None
    sumber_data: str | None = None
    frekuensi: str | None = None
    status_ketersediaan: str | None = None
    status_metadata: str | None = None
    periode_data: str | None = None
    tahun_terakhir: OpsionalInt = None
    is_proxy: bool = False
    nama_proxy: str | None = None
    status_rpjmd: str | None = None
    kode_sdgs: str | None = None
    link_metadata: str | None = None
    link_publikasi: str | None = None
    link_data: str | None = None
    catatan_teknis: str | None = None
    # Field metadata_indikator yang namanya tidak sama dengan kolom indikator
    # di atas (definisi, sumber_data, frekuensi, status_metadata SUDAH ada
    # di atas dan ditulis ke dua tabel dengan nilai yang sama).
    definisi: str | None = None
    interpretasi: str | None = None
    rumus: str | None = None
    rumus_mentah: str | None = None
    rumus_latex: str | None = None
    halaman_sumber: str | None = None
    perlu_verifikasi_manual: bool = False
    sumber_metadata: str | None = None
    nama_di_buku1: str | None = None


class IndikatorFormBuat(IndikatorFormDasar):
    id_indikator: str


class IndikatorAdminRingkas(BaseModel):
    """Satu baris daftar admin — seluruh kolom `indikator`, tanpa metadata."""

    id_indikator: str
    kategori: str
    nomor: int | None = None
    kode_indikator: str | None = None
    nama_indikator: str
    nama_asli: str | None = None
    kelompok: str | None = None
    arah_pembangunan: str | None = None
    sasaran_visi: str | None = None
    misi_agenda: str | None = None
    arah_ie: str | None = None
    indikator_induk: str | None = None
    kelompok_makro: str | None = None
    satuan: str | None = None
    penghasil: str | None = None
    kl_pengampu: str | None = None
    opd_pengampu: str | None = None
    tim_pjk: str | None = None
    sumber_data: str | None = None
    frekuensi: str | None = None
    status_ketersediaan: str | None = None
    status_metadata: str | None = None
    periode_data: str | None = None
    tahun_terakhir: int | None = None
    is_proxy: bool
    nama_proxy: str | None = None
    status_rpjmd: str | None = None
    arah_baik: str | None = None
    arah_baik_terverifikasi: bool
    kode_sdgs: str | None = None
    link_metadata: str | None = None
    link_publikasi: str | None = None
    link_data: str | None = None
    catatan_teknis: str | None = None
    # Dihitung, bukan kolom asli — lihat services.indikator.daftar_admin.
    # Frontend menonaktifkan tombol hapus saat ini true.
    punya_nilai: bool


class DaftarIndikatorAdminResponse(BaseModel):
    data: list[IndikatorAdminRingkas]
    total: int
    page: int
    page_size: int


class MetadataIndikatorAdmin(BaseModel):
    definisi: str | None = None
    interpretasi: str | None = None
    sumber_data: str | None = None
    frekuensi: str | None = None
    rumus: str | None = None
    rumus_mentah: str | None = None
    rumus_latex: str | None = None
    halaman_sumber: str | None = None
    perlu_verifikasi_manual: bool = False
    sumber_metadata: str | None = None
    nama_di_buku1: str | None = None
    status_metadata: str | None = None


class IndikatorAdminDetailResponse(IndikatorAdminRingkas):
    metadata: MetadataIndikatorAdmin | None = None


class IndikatorDibuatResponse(BaseModel):
    status: str
    id_indikator: str
