"""Perintah administratif SEBATIK.

Menggantikan seed otomatis yang dulu berjalan saat modul diimpor. Sekarang
pembuatan akun awal adalah tindakan eksplisit yang dijalankan operator saat
pemasangan::

    python -m backend.app.cli seed
    python -m backend.app.cli seed --tampilkan-sandi
"""

from __future__ import annotations

import argparse
import json
import secrets
import string
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal
from .models import KODE_PROVINSI, Peran, Wilayah
from .repositories import indikator as repo_indikator
from .repositories import pengguna as repo_pengguna
from .repositories import wilayah as repo_wilayah
from .security import hash_password

# Panjang sandi acak yang dibuat saat seed. Jauh di atas kebijakan minimum
# karena sandi ini hanya dipakai sekali sebelum wajib diganti.
PANJANG_SANDI_SEED = 20
ABJAD_SANDI = string.ascii_letters + string.digits + "!@#$%^&*-_"

WILAYAH_KALTARA: tuple[tuple[str, str, str, str | None], ...] = (
    ("65", "Kalimantan Utara", "PROVINSI", None),
    ("6501", "Bulungan", "KABUPATEN", "65"),
    ("6502", "Malinau", "KABUPATEN", "65"),
    ("6503", "Nunukan", "KABUPATEN", "65"),
    ("6504", "Tana Tidung", "KABUPATEN", "65"),
    ("6571", "Tarakan", "KOTA", "65"),
)

# Dua slot operator per wilayah, sesuai pemasangan yang berjalan sekarang.
OPERATOR_PER_WILAYAH = 2

# Fixture di-generate scripts/ekspor_seed_indikator.py dari Excel klasifikasi
# ISV/IUP, di-commit ke git supaya deploy tidak butuh Excel sama sekali.
BERKAS_SEED_INDIKATOR = Path(__file__).resolve().parent / "data" / "indikator_seed.json"
FIELD_KLASIFIKASI = ("sasaran_visi", "misi_agenda", "arah_ie", "indikator_induk")


def seed_indikator(session: Session, berkas: Path = BERKAS_SEED_INDIKATOR) -> int:
    """Isi indikator+metadata+nilai baseline dari fixture bila tabel kosong.

    Idempoten: mengembalikan 0 tanpa melakukan apa pun bila `indikator`
    sudah berisi baris apa pun — supaya redeploy tidak menduplikasi data.
    Tidak melakukan commit, sama seperti `pastikan_wilayah`/`seed_akun`.
    """
    if repo_indikator.jumlah(session) > 0:
        return 0

    muatan = json.loads(berkas.read_text(encoding="utf-8"))
    repo_indikator.seed_massal(
        session,
        indikator=muatan["indikator"],
        metadata=muatan["metadata_indikator"],
        nilai=muatan["nilai_indikator"],
    )
    session.flush()
    return len(muatan["indikator"])


def sinkronkan_klasifikasi(
    session: Session, berkas: Path = BERKAS_SEED_INDIKATOR
) -> list[tuple[str, str, object, object]]:
    """Terapkan hanya empat field kerangka dari fixture ke database terpasang.

    Fungsi ini sengaja tidak menyentuh metadata maupun nilai indikator. Commit
    tetap menjadi keputusan pemanggil agar mode pratinjau tidak dapat menulis.
    """
    muatan = json.loads(berkas.read_text(encoding="utf-8"))
    perubahan: list[tuple[str, str, object, object]] = []
    for sumber in muatan["indikator"]:
        indikator = repo_indikator.ambil(session, sumber["id_indikator"])
        if indikator is None:
            continue
        for field in FIELD_KLASIFIKASI:
            lama = getattr(indikator, field)
            baru = sumber.get(field)
            if lama != baru:
                perubahan.append((indikator.id_indikator, field, lama, baru))
                setattr(indikator, field, baru)
    session.flush()
    return perubahan


def sandi_acak(panjang: int = PANJANG_SANDI_SEED) -> str:
    """Sandi acak kriptografis; dicetak sekali lalu tidak dapat dilihat lagi."""
    return "".join(secrets.choice(ABJAD_SANDI) for _ in range(panjang))


def pastikan_wilayah(session: Session) -> int:
    """Isi wilayah yang belum ada. Idempoten."""
    dibuat = 0
    for kode, nama, tingkat, induk in WILAYAH_KALTARA:
        if session.get(Wilayah, kode) is None:
            session.add(Wilayah(kode=kode, nama=nama, tingkat=tingkat, parent_kode=induk, aktif=True))
            dibuat += 1
    session.flush()
    return dibuat


def seed_akun(session: Session) -> list[tuple[str, str]]:
    """Buat akun awal yang belum ada; kembalikan (username, sandi) yang baru.

    Akun yang sudah ada tidak disentuh sama sekali — menjalankan ulang perintah
    ini tidak boleh menyetel ulang sandi siapa pun.
    """
    baru: list[tuple[str, str]] = []

    def buat(username: str, nama: str, peran: str, wilayah_kode: str | None) -> None:
        if repo_pengguna.ambil_untuk_login(session, username) is not None:
            return
        sandi = sandi_acak()
        repo_pengguna.buat(
            session,
            username=username,
            nama=nama,
            password_hash=hash_password(sandi),
            peran=peran,
            wilayah_kode=wilayah_kode,
        )
        baru.append((username, sandi))

    buat("admin", "Administrator Awal", Peran.ADMIN, KODE_PROVINSI)
    buat("verifikator.65.1", "Verifikator Provinsi 1", Peran.VERIFIKATOR, KODE_PROVINSI)
    for kode, nama, _tingkat, _induk in WILAYAH_KALTARA:
        for nomor in range(1, OPERATOR_PER_WILAYAH + 1):
            buat(f"operator.{kode}.{nomor}", f"Operator {nama} {nomor}", Peran.OPERATOR, kode)
    session.flush()
    return baru


def perintah_seed_uji(password: str) -> int:
    """Siapkan akun berkredensial tetap hanya pada database SQLite uji lokal."""
    path = settings.sqlite_path
    nama_db = path.name.lower() if path else ""
    if settings.is_production or path is None or not any(penanda in nama_db for penanda in ("uji", "test")):
        print("DITOLAK: seed-uji hanya boleh memakai SQLite development dengan nama file mengandung 'uji' atau 'test'.")
        return 2
    if len(password) < 12:
        print("DITOLAK: password uji minimal 12 karakter.")
        return 2

    with SessionLocal() as session:
        pastikan_wilayah(session)
        seed_akun(session)
        akun = repo_pengguna.daftar_dengan_wilayah(session)
        password_hash = hash_password(password)
        for pengguna, _wilayah in akun:
            repo_pengguna.ganti_password(pengguna, password_hash, wajib_ganti=False)
            pengguna.aktif = True
        session.commit()
        print(f"Akun uji siap: {len(akun)} akun. Password bersama: {password}")
        for pengguna, wilayah in akun:
            print(f"  {pengguna.username.ljust(20)} {pengguna.peran.ljust(12)} {wilayah or '-'}")
    return 0


def perintah_seed(tampilkan_sandi: bool) -> int:
    with SessionLocal() as session:
        wilayah_baru = pastikan_wilayah(session)
        akun_baru = seed_akun(session)
        session.commit()

        print(f"Wilayah ditambahkan: {wilayah_baru}")
        print(f"Akun ditambahkan   : {len(akun_baru)}")
        if not akun_baru:
            print("Tidak ada akun baru; sandi akun yang sudah ada tidak diubah.")
            return 0

        if not tampilkan_sandi:
            print(
                "\nSandi awal TIDAK ditampilkan. Jalankan ulang dengan --tampilkan-sandi\n"
                "pada terminal yang aman untuk melihatnya, atau reset lewat panel admin."
            )
            return 0

        print("\nSandi awal berikut hanya ditampilkan SEKALI. Catat dan bagikan")
        print("lewat kanal aman; semua akun wajib menggantinya saat login pertama.\n")
        lebar = max(len(nama) for nama, _ in akun_baru)
        for username, sandi in akun_baru:
            print(f"  {username.ljust(lebar)}  {sandi}")
        return 0


def perintah_seed_indikator() -> int:
    with SessionLocal() as session:
        jumlah = seed_indikator(session)
        if jumlah == 0:
            print("Tabel indikator sudah terisi; seed dilewati.")
            return 0
        session.commit()
        print(f"Seed indikator selesai: {jumlah} indikator + nilai baseline ditambahkan.")
        return 0


def perintah_sinkronkan_klasifikasi(*, jalankan: bool) -> int:
    with SessionLocal() as session:
        perubahan = sinkronkan_klasifikasi(session)
        print(f"Perubahan field klasifikasi: {len(perubahan)}")
        for id_indikator, field, lama, baru in perubahan[:20]:
            print(f"  {id_indikator} {field}: {lama!r} -> {baru!r}")
        if len(perubahan) > 20:
            print(f"  ... dan {len(perubahan) - 20} perubahan lain")
        if not jalankan:
            session.rollback()
            print("Pratinjau saja; database tidak diubah. Tambahkan --jalankan untuk menerapkan.")
            return 0
        session.commit()
        print("Klasifikasi kerangka pembangunan berhasil diperbarui.")
        return 0


def perintah_periksa() -> int:
    """Ringkasan cepat kesiapan basis data."""
    with SessionLocal() as session:
        wilayah = repo_wilayah.daftar_aktif(session)
        akun = repo_pengguna.daftar_dengan_wilayah(session)
        wajib_ganti = [a for a, _ in akun if a.harus_ganti_password]
        print(f"Wilayah aktif      : {len(wilayah)}")
        print(f"Akun               : {len(akun)}")
        print(f"Wajib ganti sandi  : {len(wajib_ganti)}")
        if wajib_ganti:
            print("  " + ", ".join(a.username for a in wajib_ganti))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m backend.app.cli", description=__doc__)
    sub = parser.add_subparsers(dest="perintah", required=True)

    seed = sub.add_parser("seed", help="buat wilayah dan akun awal bila belum ada")
    seed.add_argument(
        "--tampilkan-sandi",
        action="store_true",
        help="cetak sandi awal ke layar (hanya di terminal yang aman)",
    )
    seed_uji = sub.add_parser("seed-uji", help="reset akun pada SQLite uji lokal ke password yang ditentukan")
    seed_uji.add_argument("--password", required=True, help="password bersama untuk seluruh akun uji")
    sub.add_parser("periksa", help="ringkasan kesiapan basis data")
    sub.add_parser(
        "seed-indikator",
        help="isi indikator+metadata+nilai baseline dari fixture bila tabel indikator kosong",
    )
    sinkronkan = sub.add_parser(
        "sinkronkan-klasifikasi",
        help="pratinjau/perbarui empat klasifikasi kerangka tanpa menyentuh nilai",
    )
    sinkronkan.add_argument(
        "--jalankan",
        action="store_true",
        help="terapkan perubahan; tanpa opsi ini hanya menampilkan pratinjau",
    )

    argumen = parser.parse_args(argv)
    if argumen.perintah == "seed":
        return perintah_seed(argumen.tampilkan_sandi)
    if argumen.perintah == "seed-uji":
        return perintah_seed_uji(argumen.password)
    if argumen.perintah == "seed-indikator":
        return perintah_seed_indikator()
    if argumen.perintah == "sinkronkan-klasifikasi":
        return perintah_sinkronkan_klasifikasi(jalankan=argumen.jalankan)
    return perintah_periksa()


if __name__ == "__main__":
    sys.exit(main())
