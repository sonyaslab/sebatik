"""Tes service.indikator: validasi CRUD admin dan orkestrasi audit."""

from __future__ import annotations

import pytest

from backend.app.schemas.indikator import IndikatorFormBuat, IndikatorFormDasar
from backend.app.services import indikator as svc


def _form_buat(**ubah) -> IndikatorFormBuat:
    baku = {"id_indikator": "ISV-999", "kategori": "ISV", "nomor": 999, "nama_indikator": "Uji"}
    return IndikatorFormBuat(**{**baku, **ubah})


def _form_dasar(**ubah) -> IndikatorFormDasar:
    baku = {"kategori": "ISV", "nomor": 999, "nama_indikator": "Uji"}
    return IndikatorFormDasar(**{**baku, **ubah})


def _pengguna(session, pengguna_id: int):
    """Akun yang diacu jejak audit harus benar-benar ada.

    `LogAktivitas.pengguna_id` dan `LogPerubahan.pengguna_id` punya FK ke
    `pengguna.id`, dan fixture `session` memakai basis data kosong dengan
    PRAGMA foreign_keys=ON — jadi pengguna_id karangan akan gagal FK.
    """
    from backend.app.models import Pengguna, Peran

    akun = Pengguna(
        id=pengguna_id,
        username=f"admin.uji.{pengguna_id}",
        nama=f"Admin Uji {pengguna_id}",
        password_hash="hash-tidak-dipakai-di-tes-ini",
        peran=Peran.ADMIN,
        wilayah_kode="65",
    )
    session.add(akun)
    session.flush()
    return akun


@pytest.mark.parametrize(
    "id_indikator,kategori,nomor,valid",
    [
        ("ISV-999", "ISV", 999, True),
        ("ISV-001", "ISV", 999, False),  # nomor tidak cocok id
        ("ISV-999", "IUP", 999, False),  # kategori tidak cocok prefiks id
        ("XYZ-001", "XYZ", 1, False),  # kategori bukan ISV/IUP
    ],
)
def test_periksa_konsistensi_id(id_indikator, kategori, nomor, valid):
    penolakan = svc.periksa_konsistensi_id(id_indikator, kategori, nomor)
    assert (penolakan is None) is valid
    if penolakan:
        assert penolakan.kode == 422


def test_periksa_konfirmasi_penghapusan_menolak_teks_yang_tidak_cocok():
    """Penjaga penghapusan kini konfirmasi eksplisit, bukan larangan sepihak.

    Admin boleh menghapus indikator berisi nilai; yang wajib adalah menyebut
    ulang id-nya, supaya penghapusan tidak pernah terjadi karena salah pencet.
    """
    penolakan = svc.periksa_konfirmasi_penghapusan("ISV-999", "ISV-000")
    assert penolakan is not None
    assert penolakan.kode == 400

    assert svc.periksa_konfirmasi_penghapusan("ISV-999", "") is not None
    assert svc.periksa_konfirmasi_penghapusan("ISV-999", "ISV-999") is None


def test_hapus_indikator_membuang_nilai_dan_usulannya(session):
    """Nilai ikut lewat CASCADE, usulan dibuang service (FK-nya tanpa ON DELETE)."""
    from backend.app.models import Indikator, NilaiIndikator, UsulanNilai

    _pengguna(session, 1)
    session.add(Indikator(id_indikator="ISV-999", kategori="ISV", nomor=999, nama_indikator="Uji"))
    session.flush()
    session.add(NilaiIndikator(id_indikator="ISV-999", wilayah_kode="65", tahun=2021, jenis="realisasi", nilai=1.0))
    session.add(
        UsulanNilai(
            id_indikator="ISV-999",
            wilayah_kode="65",
            tahun=2025,
            jenis="realisasi",
            nilai=2.0,
            sumber="Uji",
            pengusul_id=1,
        )
    )
    session.flush()

    indikator = session.get(Indikator, "ISV-999")
    assert svc.hapus_indikator(session, indikator, pengguna_id=1) == {"status": "DIHAPUS"}

    assert session.get(Indikator, "ISV-999") is None
    assert session.query(NilaiIndikator).filter_by(id_indikator="ISV-999").count() == 0
    assert session.query(UsulanNilai).filter_by(id_indikator="ISV-999").count() == 0


def test_buat_indikator_insert_dan_mencatat_aktivitas(session):
    from backend.app.models import Indikator, LogAktivitas

    _pengguna(session, 1)
    indikator = svc.buat_indikator(session, _form_buat(), pengguna_id=1)

    assert isinstance(indikator, Indikator)
    log = session.query(LogAktivitas).filter_by(objek_id="ISV-999").one()
    assert log.aksi == "indikator_dibuat"


def test_buat_indikator_menyalin_field_kembar_ke_metadata(session):
    from backend.app.models import MetadataIndikator

    _pengguna(session, 1)
    svc.buat_indikator(session, _form_buat(sumber_data="BPS", definisi="Definisi X"), pengguna_id=1)

    metadata = session.get(MetadataIndikator, "ISV-999")
    assert metadata.sumber_data == "BPS"
    assert metadata.definisi == "Definisi X"


def test_perbarui_indikator_mencatat_log_perubahan_hanya_untuk_field_berubah(session):
    from backend.app.models import LogPerubahan
    from backend.app.repositories import indikator as repo_indikator

    _pengguna(session, 1)
    _pengguna(session, 2)
    indikator = svc.buat_indikator(session, _form_buat(kelompok="Lama"), pengguna_id=1)
    session.flush()
    metadata = repo_indikator.ambil_metadata(session, "ISV-999")

    hasil = svc.perbarui_indikator(session, indikator, metadata, _form_dasar(kelompok="Baru"), pengguna_id=2)

    assert hasil["status"] == "DIPERBARUI"
    log = session.query(LogPerubahan).filter_by(id_indikator="ISV-999", field="kelompok").one()
    assert log.nilai_lama == "Lama"
    assert log.nilai_baru == "Baru"
    assert log.pengguna_id == 2


def test_hapus_indikator_mencatat_aktivitas_dan_menghapus_baris(session):
    from backend.app.models import Indikator, LogAktivitas

    _pengguna(session, 1)
    _pengguna(session, 2)
    indikator = svc.buat_indikator(session, _form_buat(), pengguna_id=1)
    session.flush()

    hasil = svc.hapus_indikator(session, indikator, pengguna_id=2)

    assert hasil == {"status": "DIHAPUS"}
    assert session.get(Indikator, "ISV-999") is None
    log = session.query(LogAktivitas).filter_by(objek_id="ISV-999", aksi="indikator_dihapus").one()
    assert log.pengguna_id == 2


def test_daftar_admin_menandai_punya_nilai_dengan_benar(session):
    from backend.app.models import NilaiIndikator

    _pengguna(session, 1)
    svc.buat_indikator(session, _form_buat(), pengguna_id=1)
    svc.buat_indikator(session, _form_buat(id_indikator="ISV-998", nomor=998), pengguna_id=1)
    session.add(NilaiIndikator(id_indikator="ISV-999", wilayah_kode="65", tahun=2021, jenis="realisasi", nilai=1.0))
    session.commit()

    hasil = svc.daftar_admin(
        session,
        q=None,
        kategori=None,
        kelompok=None,
        tim=None,
        sort="id_indikator",
        order="asc",
        page=1,
        page_size=200,
    )
    per_id = {baris["id_indikator"]: baris for baris in hasil["data"]}
    assert per_id["ISV-999"]["punya_nilai"] is True
    assert per_id["ISV-998"]["punya_nilai"] is False


def test_detail_admin_menyertakan_metadata(session):
    _pengguna(session, 1)
    indikator = svc.buat_indikator(session, _form_buat(definisi="Definisi Y"), pengguna_id=1)
    session.commit()

    hasil = svc.detail_admin(session, indikator)
    assert hasil["metadata"]["definisi"] == "Definisi Y"
    assert hasil["punya_nilai"] is False
