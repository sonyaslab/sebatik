"""Tes repository.indikator: cek nilai massal, buat, perbarui, hapus."""

from __future__ import annotations

from backend.app.repositories import indikator as repo_indikator


def _indikator_dasar(session, id_indikator="ISV-999", **ubah):
    from backend.app.models import Indikator

    baku = {"id_indikator": id_indikator, "kategori": "ISV", "nomor": 999, "nama_indikator": "Uji"}
    obj = Indikator(**{**baku, **ubah})
    session.add(obj)
    session.flush()
    return obj


def test_punya_nilai_false_saat_tidak_ada_nilai(session):
    _indikator_dasar(session)
    assert repo_indikator.punya_nilai(session, "ISV-999") is False


def test_punya_nilai_true_saat_ada_nilai(session):
    from backend.app.models import NilaiIndikator

    _indikator_dasar(session)
    session.add(NilaiIndikator(id_indikator="ISV-999", wilayah_kode="65", tahun=2021, jenis="realisasi", nilai=1.0))
    session.flush()
    assert repo_indikator.punya_nilai(session, "ISV-999") is True


def test_id_dengan_nilai_hanya_mengembalikan_yang_punya_nilai(session):
    from backend.app.models import NilaiIndikator

    _indikator_dasar(session, "ISV-999")
    _indikator_dasar(session, "ISV-998", nomor=998)
    session.add(NilaiIndikator(id_indikator="ISV-999", wilayah_kode="65", tahun=2021, jenis="realisasi", nilai=1.0))
    session.flush()

    assert repo_indikator.id_dengan_nilai(session, ["ISV-999", "ISV-998"]) == {"ISV-999"}


def test_id_dengan_nilai_kosong_untuk_daftar_kosong(session):
    assert repo_indikator.id_dengan_nilai(session, []) == set()


def test_buat_insert_indikator_dan_metadata(session):
    from backend.app.models import Indikator, MetadataIndikator

    indikator = repo_indikator.buat(
        session,
        indikator_fields={
            "id_indikator": "ISV-999",
            "kategori": "ISV",
            "nomor": 999,
            "nama_indikator": "Baru",
        },
        metadata_fields={"definisi": "Definisi baru"},
    )
    session.flush()

    assert indikator.id_indikator == "ISV-999"
    assert session.get(Indikator, "ISV-999").nama_indikator == "Baru"
    assert session.get(MetadataIndikator, "ISV-999").definisi == "Definisi baru"


def test_perbarui_hanya_mencatat_field_yang_benar_benar_berubah(session):
    from backend.app.models import MetadataIndikator

    indikator = _indikator_dasar(session, nama_indikator="Lama", kelompok="Kelompok Lama")
    metadata = MetadataIndikator(id_indikator="ISV-999", definisi="Definisi lama")
    session.add(metadata)
    session.flush()

    perubahan = repo_indikator.perbarui(
        session,
        indikator,
        metadata,
        indikator_fields={
            "kategori": "ISV",
            "nomor": 999,
            "nama_indikator": "Lama",
            "kelompok": "Kelompok Baru",
        },
        metadata_fields={"definisi": "Definisi lama"},
    )

    assert perubahan == {"kelompok": ("Kelompok Lama", "Kelompok Baru")}
    assert indikator.nama_indikator == "Lama"
    assert indikator.kelompok == "Kelompok Baru"


def test_perbarui_membuat_baris_metadata_bila_belum_ada(session):
    from backend.app.models import MetadataIndikator

    indikator = _indikator_dasar(session)

    repo_indikator.perbarui(
        session,
        indikator,
        None,
        indikator_fields={"kategori": "ISV", "nomor": 999, "nama_indikator": "Uji"},
        metadata_fields={"definisi": "Definisi baru"},
    )
    session.flush()

    assert session.get(MetadataIndikator, "ISV-999").definisi == "Definisi baru"


def test_hapus_menghapus_indikator(session):
    from backend.app.models import Indikator

    indikator = _indikator_dasar(session)
    repo_indikator.hapus(session, indikator)
    session.flush()

    assert session.get(Indikator, "ISV-999") is None


def test_hapus_ikut_menghapus_metadata_lewat_cascade(session):
    from backend.app.models import Indikator, MetadataIndikator

    indikator = _indikator_dasar(session)
    session.add(MetadataIndikator(id_indikator="ISV-999"))
    session.flush()

    repo_indikator.hapus(session, indikator)
    session.flush()

    assert session.get(Indikator, "ISV-999") is None
    assert session.get(MetadataIndikator, "ISV-999") is None
