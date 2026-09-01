"""Query terhadap dimensi indikator dan metadatanya."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Select, asc, desc, func, insert, select
from sqlalchemy.orm import Session

from ..models import Indikator, MetadataIndikator, NilaiIndikator, StatusVerifikasi

# Kolom yang boleh keluar lewat endpoint publik `/indikator`. Nama PIC
# perorangan dan status ketersediaan sengaja tidak termasuk.
FIELD_PUBLIK = (
    "id_indikator",
    "nama_indikator",
    "kategori",
    "kelompok",
    "satuan",
    "tim_pjk",
    "opd_pengampu",
    "status_metadata",
    "tahun_terakhir",
    "is_proxy",
)


def _terverifikasi(stmt: Select) -> Select:
    """Filter yang berulang di hampir semua pembacaan publik."""
    return stmt.where(Indikator.status_verifikasi == StatusVerifikasi.DISETUJUI)


def ambil(session: Session, id_indikator: str) -> Indikator | None:
    return session.get(Indikator, id_indikator)


def ambil_terverifikasi(session: Session, id_indikator: str) -> Indikator | None:
    stmt = _terverifikasi(select(Indikator).where(Indikator.id_indikator == id_indikator))
    return session.scalars(stmt).first()


def ada(session: Session, id_indikator: str) -> bool:
    stmt = select(Indikator.id_indikator).where(Indikator.id_indikator == id_indikator)
    return session.scalars(stmt).first() is not None


def jumlah(session: Session) -> int:
    """Jumlah baris `indikator`. Dipakai CLI untuk cek idempotensi seed awal."""
    return session.scalar(select(func.count()).select_from(Indikator)) or 0


def semua_ringkas(session: Session) -> list[Indikator]:
    """Daftar indikator tanpa relasi; dipakai validasi unggahan massal."""
    return list(session.scalars(select(Indikator).order_by(Indikator.id_indikator)))


def seed_massal(
    session: Session,
    indikator: list[dict[str, object]],
    metadata: list[dict[str, object]],
    nilai: list[dict[str, object]],
) -> None:
    """Insert massal indikator+metadata+nilai dari fixture seed awal.

    Urutan tabel penting: `metadata_indikator` dan `nilai_indikator` punya FK
    ke `indikator.id_indikator`, jadi `indikator` harus masuk lebih dulu.
    Tidak melakukan commit — pemanggil (CLI) yang memutuskan kapan commit,
    sama seperti pola `seed_akun`/`pastikan_wilayah` di `cli.py`.
    """
    if indikator:
        session.execute(insert(Indikator), indikator)
    if metadata:
        session.execute(insert(MetadataIndikator), metadata)
    if nilai:
        session.execute(insert(NilaiIndikator), nilai)


def _saring(
    stmt: Select,
    q: str | None = None,
    kategori: Sequence[str] | None = None,
    kelompok: Sequence[str] | None = None,
    tim: Sequence[str] | None = None,
    status_metadata: Sequence[str] | None = None,
) -> Select:
    if q:
        stmt = stmt.where(Indikator.nama_indikator.ilike(f"%{q}%"))
    if kategori:
        stmt = stmt.where(Indikator.kategori.in_(kategori))
    if kelompok:
        stmt = stmt.where(Indikator.kelompok.in_(kelompok))
    if tim:
        stmt = stmt.where(Indikator.tim_pjk.in_(tim))
    if status_metadata:
        stmt = stmt.where(Indikator.status_metadata.in_(status_metadata))
    return stmt


def cari(
    session: Session,
    *,
    q: str | None = None,
    kategori: Sequence[str] | None = None,
    kelompok: Sequence[str] | None = None,
    tim: Sequence[str] | None = None,
    status_metadata: Sequence[str] | None = None,
    sort: str = "id_indikator",
    order: str = "asc",
    page: int = 1,
    page_size: int = 25,
    hanya_terverifikasi: bool = False,
) -> tuple[list[Indikator], int]:
    """Halaman hasil beserta totalnya (untuk endpoint `/indikator`).

    Saringan status ikut sebagai parameter, bukan dipasang mati: pemanggilnya
    ada dua — katalog publik yang hanya boleh melihat indikator disetujui, dan
    CRUD admin yang justru perlu melihat drafnya.
    """

    def disaring(stmt: Select) -> Select:
        return _saring(stmt, q, kategori, kelompok, tim, status_metadata)

    # `is_proxy` boolean tidak berguna sebagai kunci urut dan tidak pernah
    # dikirim frontend; jatuhkan ke id_indikator bila diminta.
    kolom_urut = {nama: getattr(Indikator, nama) for nama in FIELD_PUBLIK if nama != "is_proxy"}
    kolom = kolom_urut.get(sort, Indikator.id_indikator)
    arah = desc if order == "desc" else asc

    stmt = disaring(select(Indikator))
    hitung = disaring(select(func.count()).select_from(Indikator))
    if hanya_terverifikasi:
        stmt = _terverifikasi(stmt)
        hitung = _terverifikasi(hitung)

    daftar = session.scalars(stmt.order_by(arah(kolom)).offset((page - 1) * page_size).limit(page_size)).all()
    total = session.scalar(hitung) or 0
    return list(daftar), total


def daftar_ekspor(session: Session) -> list[Indikator]:
    """Urutan ekspor: IUP lalu ISV (kategori menurun), lalu nomor urut.

    Pemanggilnya semuanya publik (`/capaian` dan unduhan), jadi saringannya
    tetap di sini dan tidak perlu jadi parameter.
    """
    stmt = _terverifikasi(select(Indikator)).order_by(Indikator.kategori.desc(), Indikator.nomor)
    return list(session.scalars(stmt))


def daftar_terverifikasi(session: Session) -> list[Indikator]:
    stmt = _terverifikasi(select(Indikator)).order_by(Indikator.id_indikator)
    return list(session.scalars(stmt))


def daftar_makro(session: Session) -> list[Indikator]:
    """Indikator berklasifikasi makro, ISV lebih dulu (kategori menurun)."""
    stmt = _terverifikasi(select(Indikator).where(Indikator.kelompok_makro.like("Makro%"))).order_by(
        Indikator.kategori.desc(), Indikator.id_indikator
    )
    return list(session.scalars(stmt))


def daftar_sasaran_visi(session: Session) -> list[Indikator]:
    stmt = _terverifikasi(select(Indikator).where(Indikator.kategori == "ISV")).order_by(Indikator.id_indikator)
    return list(session.scalars(stmt))


def id_berklasifikasi(session: Session, kolom: str) -> list[str]:
    """ID indikator yang punya isi bermakna pada kolom klasifikasi tertentu.

    Nilai kosong dan penanda strip (`-`, `- belum ditetapkan`) dianggap belum
    diklasifikasikan, sama seperti perhitungan ketersediaan sebelumnya.
    """
    atribut = getattr(Indikator, kolom)
    stmt = _terverifikasi(
        select(Indikator.id_indikator).where(
            atribut.is_not(None),
            func.trim(atribut) != "",
            atribut.not_like("-%"),
        )
    )
    return list(session.scalars(stmt))


def daftar_berklasifikasi(session: Session, kolom: str) -> list[Indikator]:
    """Indikator terverifikasi yang memiliki klasifikasi pada ``kolom``."""
    atribut = getattr(Indikator, kolom)
    stmt = _terverifikasi(
        select(Indikator).where(
            atribut.is_not(None),
            func.trim(atribut) != "",
            atribut.not_like("-%"),
        )
    ).order_by(Indikator.kategori.desc(), Indikator.id_indikator)
    return list(session.scalars(stmt))


def daftar_arah_terverifikasi(session: Session) -> list[Indikator]:
    """Indikator yang arah baiknya sudah dikonfirmasi admin.

    Hanya indikator ini yang boleh masuk peringkat: tanpa arah yang pasti,
    "membaik" dan "memburuk" tidak dapat dibedakan.
    """
    stmt = select(Indikator).where(Indikator.arah_baik_terverifikasi.is_(True))
    return list(session.scalars(stmt))


def ambil_metadata(session: Session, id_indikator: str) -> MetadataIndikator | None:
    return session.get(MetadataIndikator, id_indikator)


def ubah_arah_baik(indikator: Indikator, arah_baik: str) -> str | None:
    """Set arah baik sebagai terverifikasi; mengembalikan nilai lama untuk log audit.

    Menerima objek, bukan id, supaya "indikator tidak ditemukan" ditangani
    pemanggil dan tidak tertukar dengan "arah lama memang NULL".
    """
    lama = indikator.arah_baik
    indikator.arah_baik = arah_baik
    indikator.arah_baik_terverifikasi = True
    return lama


def punya_nilai(session: Session, id_indikator: str) -> bool:
    stmt = select(NilaiIndikator.id).where(NilaiIndikator.id_indikator == id_indikator).limit(1)
    return session.scalars(stmt).first() is not None


def id_dengan_nilai(session: Session, ids: Sequence[str]) -> set[str]:
    """Subset dari `ids` yang punya minimal satu baris `nilai_indikator`.

    Satu query untuk seluruh halaman, bukan satu query per baris — daftar
    admin bisa memuat 200 baris sekaligus dan tiap baris butuh penanda ini
    untuk mengaktifkan/menonaktifkan tombol hapusnya.
    """
    if not ids:
        return set()
    stmt = select(NilaiIndikator.id_indikator.distinct()).where(NilaiIndikator.id_indikator.in_(ids))
    return set(session.scalars(stmt))


def pilihan_klasifikasi(session: Session, field: str) -> list[str]:
    """Nilai klasifikasi yang benar-benar dipakai master indikator."""
    atribut = getattr(Indikator, field)
    stmt = (
        select(atribut)
        .where(atribut.is_not(None), func.trim(atribut) != "", atribut.not_like("-%"))
        .distinct()
        .order_by(atribut)
    )
    return list(session.scalars(stmt))


def buat(
    session: Session,
    indikator_fields: dict[str, object],
    metadata_fields: dict[str, object],
) -> Indikator:
    """Buat indikator+metadata baru. Tidak commit — pemanggil (service) yang commit."""
    indikator = Indikator(**indikator_fields)
    session.add(indikator)
    session.flush()  # perlu id_indikator terisi sebelum baris metadata dibuat
    session.add(MetadataIndikator(id_indikator=indikator.id_indikator, **metadata_fields))
    return indikator


def perbarui(
    session: Session,
    indikator: Indikator,
    metadata: MetadataIndikator | None,
    indikator_fields: dict[str, object],
    metadata_fields: dict[str, object],
) -> dict[str, tuple[object, object]]:
    """Terapkan field baru; kembalikan {field: (lama, baru)} hanya utk field yang berubah.

    Dipakai pemanggil (service) untuk menulis satu baris LogPerubahan per
    field yang benar-benar berubah nilainya — form ini full-replace, jadi
    sebagian besar field dikirim ulang tanpa berubah setiap kali disimpan.
    """
    perubahan: dict[str, tuple[object, object]] = {}

    for field, baru in indikator_fields.items():
        lama = getattr(indikator, field)
        if lama != baru:
            perubahan[field] = (lama, baru)
            setattr(indikator, field, baru)

    if metadata is None:
        metadata = MetadataIndikator(id_indikator=indikator.id_indikator)
        session.add(metadata)
    for field, baru in metadata_fields.items():
        lama = getattr(metadata, field)
        if lama != baru:
            perubahan[f"metadata.{field}"] = (lama, baru)
            setattr(metadata, field, baru)

    return perubahan


def hapus(session: Session, indikator: Indikator) -> None:
    """Hapus indikator; `metadata_indikator` ikut terhapus lewat FK CASCADE.

    Lihat `ondelete="CASCADE"` di backend/app/models/indikator.py — tidak
    perlu dihapus manual di sini. Pemanggil (service) yang memastikan lewat
    `punya_nilai()` bahwa indikator ini memang boleh dihapus SEBELUM
    memanggil fungsi ini.
    """
    session.delete(indikator)
