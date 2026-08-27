"""Penyusunan muatan indikator: daftar publik, detail, dan metadata.

Termasuk aturan kecil yang tidak boleh tinggal di router: kolom mana yang
boleh keluar ke publik, nama kolom lama yang masih dipertahankan demi kontrak,
dan kapan sebuah metadata layak disebut "tersedia" (backend.md §1.2).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..models import KODE_PROVINSI, ArahBaik, Indikator, MetadataIndikator
from ..repositories import indikator as repo_indikator
from ..repositories import nilai as repo_nilai
from ..repositories import tata_kelola as repo_tata_kelola
from ..schemas.indikator import IndikatorFormBuat, IndikatorFormDasar
from . import Penolakan
from . import capaian as svc_capaian

# Kolom yang boleh keluar lewat daftar publik. Nama PIC perorangan dan status
# ketersediaan sengaja tidak termasuk.
FIELD_PUBLIK = repo_indikator.FIELD_PUBLIK

# Kompatibilitas kontrak: kolom basis data dibakukan menjadi `opd_pengampu`,
# tetapi frontend lama masih membaca `opd_penanggung_jawab`.
NAMA_LAMA = {"opd_pengampu": "opd_penanggung_jawab"}

# Isi metadata yang menentukan apakah metadata dianggap benar-benar tersedia.
FIELD_METADATA_BERMAKNA = ("definisi", "rumus_mentah", "interpretasi", "sumber_data", "frekuensi")


def ringkas(indikator: Indikator) -> dict[str, Any]:
    """Satu baris daftar publik, dengan nama kolom lama dipertahankan."""
    return {NAMA_LAMA.get(f, f): getattr(indikator, f) for f in FIELD_PUBLIK}


def cari(
    session: Session,
    *,
    q: str | None,
    kategori: list[str] | None,
    kelompok: list[str] | None,
    tim: list[str] | None,
    status_metadata: list[str] | None,
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Daftar indikator publik berhalaman."""
    daftar, total = repo_indikator.cari(
        session,
        q=q,
        kategori=kategori,
        kelompok=kelompok,
        tim=tim,
        status_metadata=status_metadata,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )
    return {
        "data": [ringkas(item) for item in daftar],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def detail(session: Session, indikator: Indikator) -> dict[str, Any]:
    """Ringkasan capaian + seri nilai provinsi + metadata teknis."""
    id_indikator = indikator.id_indikator
    muatan = svc_capaian.muatan(session, indikator)
    muatan["nilai"] = [
        {
            "tahun": baris.tahun,
            "jenis": baris.jenis,
            "nilai": baris.nilai,
            # Nama lama dipertahankan sampai frontend diselaraskan.
            "sumber_sheet": baris.sumber,
        }
        for baris in repo_nilai.seri(session, id_indikator, KODE_PROVINSI)
    ]
    metadata = repo_indikator.ambil_metadata(session, id_indikator)
    muatan["metadata"] = (
        None
        if metadata is None
        else {
            "definisi": metadata.definisi,
            "rumus_mentah": metadata.rumus_mentah,
            "interpretasi": metadata.interpretasi,
            "sumber_data": metadata.sumber_data,
            "frekuensi": metadata.frekuensi,
            "halaman_sumber": metadata.halaman_sumber,
            "sumber_metadata": metadata.sumber_metadata,
            "perlu_verifikasi_manual": metadata.perlu_verifikasi_manual,
        }
    )
    return muatan


def metadata_lengkap(session: Session, indikator: Indikator) -> dict[str, Any]:
    """Muatan `/beranda-indikator/{id}/metadata`."""
    id_indikator = indikator.id_indikator
    metadata = repo_indikator.ambil_metadata(session, id_indikator)
    isi_metadata = (
        None
        if metadata is None
        else {
            "definisi": _ringkas_metadata(metadata.definisi),
            "rumus_mentah": metadata.rumus_mentah,
            "rumus_latex": metadata.rumus_latex,
            "keterangan_rumus": _baris(metadata.rumus),
            "perlu_verifikasi_rumus": bool(metadata.rumus_latex) and metadata.perlu_verifikasi_manual,
            "halaman_sumber": metadata.halaman_sumber,
            "interpretasi": _ringkas_metadata(metadata.interpretasi),
            "sumber_data": metadata.sumber_data,
            "frekuensi": metadata.frekuensi,
            "status_metadata": metadata.status_metadata,
            "sumber_metadata": metadata.sumber_metadata,
        }
    )
    # "Tersedia" berarti ada isi yang bermakna, bukan sekadar barisnya ada.
    tersedia = bool(isi_metadata and any(isi_metadata.get(kunci) for kunci in FIELD_METADATA_BERMAKNA))
    return {
        "id_indikator": indikator.id_indikator,
        "kategori": indikator.kategori,
        "kode_indikator": indikator.kode_indikator,
        "nama_indikator": indikator.nama_indikator,
        "kelompok": indikator.kelompok,
        "arah_pembangunan": indikator.arah_pembangunan,
        "satuan": indikator.satuan,
        "opd_pengampu": indikator.opd_pengampu,
        "status_ketersediaan": indikator.status_ketersediaan,
        "periode_data": indikator.periode_data,
        "metadata": isi_metadata,
        "metadata_tersedia": tersedia,
        "nilai": [
            {
                "tahun": baris.tahun,
                "jenis": baris.jenis,
                "nilai": baris.nilai,
                "nilai_teks": baris.nilai_teks,
                "satuan_catatan": baris.satuan_catatan,
            }
            for baris in repo_nilai.seri_lengkap(session, id_indikator, KODE_PROVINSI)
        ],
    }


def _ringkas_metadata(teks: str | None, batas: int = 700) -> str | None:
    """Ringkas uraian buku pada batas kalimat agar modal tetap mudah dipindai."""
    if not teks or len(teks) <= batas:
        return teks
    potongan = teks[:batas]
    akhir = max(potongan.rfind(". "), potongan.rfind("; "))
    return potongan[: akhir + 1 if akhir > batas // 2 else batas].strip() + "…"


def _baris(teks: str | None) -> list[str]:
    """Pecah keterangan notasi yang disimpan sebagai satu kolom multi-baris.

    Rumus dan keterangannya datang dari `data/processed/rumus_latex_buku1.json` lewat
    `scripts/perbarui_rumus_latex.py`, bukan lagi dari daftar rumus bawaan yang
    dulu ditulis di berkas ini. Daftar itu hanya menutupi lima indikator dan
    tidak punya jejak halaman sumber; sekarang seluruh 86 indikator terlayani
    dari satu berkas data yang bisa diperiksa terhadap Buku 1.
    """
    return [baris.strip() for baris in (teks or "").splitlines() if baris.strip()]


def arah_baik_sah(arah_baik: str) -> bool:
    return arah_baik in tuple(ArahBaik)


def koreksi_arah_baik(
    session: Session,
    indikator: Indikator,
    *,
    arah_baik: str,
    pengguna_id: int | None,
) -> dict[str, Any]:
    """Koreksi arah baik oleh admin, beserta jejak perubahannya."""
    lama = repo_indikator.ubah_arah_baik(indikator, arah_baik)
    repo_tata_kelola.catat_perubahan(
        session,
        pengguna_id=pengguna_id,
        id_indikator=indikator.id_indikator,
        field="arah_baik",
        nilai_lama=lama,
        nilai_baru=arah_baik,
        sumber_perubahan="koreksi_admin",
    )
    session.commit()
    return {"status": "ok", "id_indikator": indikator.id_indikator, "arah_baik": arah_baik}


# --- CRUD admin -------------------------------------------------------------
#
# Field indikator yang boleh diisi/diedit lewat form admin. `arah_baik` dan
# `arah_baik_terverifikasi` sengaja TIDAK di sini — itu tetap lewat
# koreksi_arah_baik()/endpoint /arah-baik/{id} yang sudah ada, supaya tidak
# ada dua jalur yang menulis field yang sama. `status_verifikasi` juga tidak
# di sini — selalu DISETUJUI untuk data yang ditulis admin.
FIELD_INDIKATOR_EDITABLE = (
    "kategori",
    "nomor",
    "kode_indikator",
    "nama_indikator",
    "nama_asli",
    "kelompok",
    "arah_pembangunan",
    "sasaran_visi",
    "misi_agenda",
    "arah_ie",
    "indikator_induk",
    "kelompok_makro",
    "satuan",
    "penghasil",
    "kl_pengampu",
    "opd_pengampu",
    "tim_pjk",
    "sumber_data",
    "frekuensi",
    "status_ketersediaan",
    "status_metadata",
    "periode_data",
    "tahun_terakhir",
    "is_proxy",
    "nama_proxy",
    "status_rpjmd",
    "kode_sdgs",
    "link_metadata",
    "link_publikasi",
    "link_data",
    "catatan_teknis",
)
# Field metadata_indikator yang boleh diedit. sumber_data/frekuensi/
# status_metadata sengaja SAMA NAMA dengan tiga field indikator di atas —
# _pisahkan_field() menyalin nilai form yang sama ke dua tabel itu.
FIELD_METADATA_EDITABLE = (
    "definisi",
    "interpretasi",
    "sumber_data",
    "frekuensi",
    "rumus",
    "rumus_mentah",
    "rumus_latex",
    "halaman_sumber",
    "perlu_verifikasi_manual",
    "sumber_metadata",
    "nama_di_buku1",
    "status_metadata",
)


def _kosong_jadi_none(nilai: Any) -> Any:
    """String kosong dari form berarti kosongkan field, bukan literal string kosong."""
    if isinstance(nilai, str) and nilai.strip() == "":
        return None
    return nilai


def _pisahkan_field(form: IndikatorFormDasar) -> tuple[dict[str, Any], dict[str, Any]]:
    """Form gabungan -> (field utk tabel indikator, field utk metadata_indikator)."""
    muatan = form.model_dump()
    indikator_fields = {f: _kosong_jadi_none(muatan[f]) for f in FIELD_INDIKATOR_EDITABLE}
    metadata_fields = {f: _kosong_jadi_none(muatan[f]) for f in FIELD_METADATA_EDITABLE}
    return indikator_fields, metadata_fields


def periksa_konsistensi_id(id_indikator: str, kategori: str, nomor: int) -> Penolakan | None:
    """`id_indikator` harus selalu `kategori-nomor` 3 digit; dicek di create DAN update.

    Dipanggil dengan id_indikator dari form saat create, dan dari path saat
    update (lihat backend/app/routers/admin.py) — supaya submit yang mencoba
    mengubah kategori/nomor jadi tidak konsisten dengan id_indikator yang
    sudah ada (primary key, tidak pernah berubah) ditolak.
    """
    if kategori not in ("ISV", "IUP"):
        return Penolakan(422, "Kategori harus ISV atau IUP")
    diharapkan = f"{kategori}-{nomor:03d}"
    if id_indikator != diharapkan:
        return Penolakan(
            422,
            f"id_indikator harus konsisten dengan kategori+nomor (diharapkan {diharapkan}, dapat {id_indikator})",
        )
    return None


def opsi_form_admin(session: Session) -> dict[str, list[str]]:
    return {
        "kelompok": repo_indikator.pilihan_klasifikasi(session, "kelompok"),
        "kelompok_makro": repo_indikator.pilihan_klasifikasi(session, "kelompok_makro"),
    }


def periksa_pilihan_klasifikasi(
    session: Session,
    *,
    kelompok: str | None,
    kelompok_makro: str | None,
) -> Penolakan | None:
    for label, field, nilai in (
        ("Kelompok / pilar", "kelompok", kelompok),
        ("Kelompok makro", "kelompok_makro", kelompok_makro),
    ):
        if nilai and nilai not in repo_indikator.pilihan_klasifikasi(session, field):
            return Penolakan(422, f"{label} tidak termasuk pilihan master")
    return None


def periksa_konfirmasi_penghapusan(id_indikator: str, konfirmasi: str) -> Penolakan | None:
    if konfirmasi != id_indikator:
        return Penolakan(400, f"Ketik {id_indikator} sebagai konfirmasi penghapusan")
    return None


def buat_indikator(session: Session, form: IndikatorFormBuat, *, pengguna_id: int | None) -> Indikator:
    indikator_fields, metadata_fields = _pisahkan_field(form)
    indikator_fields["id_indikator"] = form.id_indikator
    indikator = repo_indikator.buat(session, indikator_fields, metadata_fields)
    repo_tata_kelola.catat_aktivitas(
        session,
        pengguna_id=pengguna_id,
        aksi="indikator_dibuat",
        objek_tipe="indikator",
        objek_id=indikator.id_indikator,
        detail=None,
    )
    session.commit()
    return indikator


def perbarui_indikator(
    session: Session,
    indikator: Indikator,
    metadata: MetadataIndikator | None,
    form: IndikatorFormDasar,
    *,
    pengguna_id: int | None,
) -> dict[str, Any]:
    indikator_fields, metadata_fields = _pisahkan_field(form)
    perubahan = repo_indikator.perbarui(session, indikator, metadata, indikator_fields, metadata_fields)
    for field, (lama, baru) in perubahan.items():
        repo_tata_kelola.catat_perubahan(
            session,
            pengguna_id=pengguna_id,
            id_indikator=indikator.id_indikator,
            field=field,
            nilai_lama=str(lama) if lama is not None else None,
            nilai_baru=str(baru) if baru is not None else None,
            sumber_perubahan="edit_admin",
        )
    session.commit()
    return {"status": "DIPERBARUI"}


def hapus_indikator(session: Session, indikator: Indikator, *, pengguna_id: int | None) -> dict[str, str]:
    id_indikator = indikator.id_indikator
    repo_tata_kelola.catat_aktivitas(
        session,
        pengguna_id=pengguna_id,
        aksi="indikator_dihapus",
        objek_tipe="indikator",
        objek_id=id_indikator,
        detail={"nama_indikator": indikator.nama_indikator, "kategori": indikator.kategori},
    )
    # `log_perubahan` append-only dan FK-nya tanpa ON DELETE: barisnya
    # dilepaskan (id_indikator dikosongkan), bukan dihapus, supaya riwayat
    # suntingan tetap ada setelah indikatornya hilang.
    repo_tata_kelola.lepaskan_log_perubahan(session, id_indikator)
    repo_tata_kelola.hapus_usulan_indikator(session, id_indikator)
    repo_indikator.hapus(session, indikator)
    session.commit()
    return {"status": "DIHAPUS"}


def _ringkas_admin(indikator: Indikator, punya_nilai: bool) -> dict[str, Any]:
    """Satu baris daftar/detail admin: seluruh kolom indikator, bukan FIELD_PUBLIK.

    Sengaja terpisah dari `ringkas()` di atas — yang publik menyembunyikan
    kolom internal (catatan_teknis, link_metadata, status_rpjmd) yang tidak
    boleh bocor ke endpoint publik `/indikator`.
    """
    return {
        "id_indikator": indikator.id_indikator,
        "kategori": indikator.kategori,
        "nomor": indikator.nomor,
        "kode_indikator": indikator.kode_indikator,
        "nama_indikator": indikator.nama_indikator,
        "nama_asli": indikator.nama_asli,
        "kelompok": indikator.kelompok,
        "arah_pembangunan": indikator.arah_pembangunan,
        "sasaran_visi": indikator.sasaran_visi,
        "misi_agenda": indikator.misi_agenda,
        "arah_ie": indikator.arah_ie,
        "indikator_induk": indikator.indikator_induk,
        "kelompok_makro": indikator.kelompok_makro,
        "satuan": indikator.satuan,
        "penghasil": indikator.penghasil,
        "kl_pengampu": indikator.kl_pengampu,
        "opd_pengampu": indikator.opd_pengampu,
        "tim_pjk": indikator.tim_pjk,
        "sumber_data": indikator.sumber_data,
        "frekuensi": indikator.frekuensi,
        "status_ketersediaan": indikator.status_ketersediaan,
        "status_metadata": indikator.status_metadata,
        "periode_data": indikator.periode_data,
        "tahun_terakhir": indikator.tahun_terakhir,
        "is_proxy": indikator.is_proxy,
        "nama_proxy": indikator.nama_proxy,
        "status_rpjmd": indikator.status_rpjmd,
        "arah_baik": indikator.arah_baik,
        "arah_baik_terverifikasi": indikator.arah_baik_terverifikasi,
        "kode_sdgs": indikator.kode_sdgs,
        "link_metadata": indikator.link_metadata,
        "link_publikasi": indikator.link_publikasi,
        "link_data": indikator.link_data,
        "catatan_teknis": indikator.catatan_teknis,
        "punya_nilai": punya_nilai,
    }


def daftar_admin(
    session: Session,
    *,
    q: str | None,
    kategori: list[str] | None,
    kelompok: list[str] | None,
    tim: list[str] | None,
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """Daftar admin berhalaman — semua kolom indikator, bukan hanya FIELD_PUBLIK."""
    daftar, total = repo_indikator.cari(
        session,
        q=q,
        kategori=kategori,
        kelompok=kelompok,
        tim=tim,
        status_metadata=None,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )
    dengan_nilai = repo_indikator.id_dengan_nilai(session, [item.id_indikator for item in daftar])
    return {
        "data": [_ringkas_admin(item, item.id_indikator in dengan_nilai) for item in daftar],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def detail_admin(session: Session, indikator: Indikator) -> dict[str, Any]:
    metadata = repo_indikator.ambil_metadata(session, indikator.id_indikator)
    hasil = _ringkas_admin(indikator, repo_indikator.punya_nilai(session, indikator.id_indikator))
    hasil["metadata"] = (
        None
        if metadata is None
        else {
            "definisi": metadata.definisi,
            "interpretasi": metadata.interpretasi,
            "sumber_data": metadata.sumber_data,
            "frekuensi": metadata.frekuensi,
            "rumus": metadata.rumus,
            "rumus_mentah": metadata.rumus_mentah,
            "rumus_latex": metadata.rumus_latex,
            "halaman_sumber": metadata.halaman_sumber,
            "perlu_verifikasi_manual": metadata.perlu_verifikasi_manual,
            "sumber_metadata": metadata.sumber_metadata,
            "nama_di_buku1": metadata.nama_di_buku1,
            "status_metadata": metadata.status_metadata,
        }
    )
    return hasil
