"""Dataset database tervalidasi untuk memuat skema aplikasi SEBATIK.

Bentuk kanonisnya tetap JSON terstandar berversi dengan ID master tiga digit
dan tabel target. Yang berubah sejak fitur unggah admin: `.xlsx` kini boleh
masuk lewat gerbang API dan CLI, dikonversi lebih dulu oleh `src/etl/excel.py`.
Yang TIDAK berubah adalah ketatnya pemeriksaan — apa pun jalur masuknya, setiap
dataset wajib lolos `validasi_dataset()` sebelum menyentuh basis data. PDF tetap
berhenti di zona sumber.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .klasifikasi import klasifikasi_kerangka

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

VERSI_SKEMA = "sebatik.database/v1"
POLA_ID = re.compile(r"^(ISV|IUP)-\d{3}$")
JUMLAH_INDIKATOR = 86
KODE_PROVINSI = "65"
JENIS_NILAI = ("realisasi", "target")
STATUS_DISETUJUI = "DISETUJUI"


class DatasetTidakValid(ValueError):
    """Dataset melanggar kontrak data dan tidak boleh dimuat."""


def _teks(nilai: Any) -> str | None:
    if nilai is None:
        return None
    hasil = re.sub(r"\s+", " ", str(nilai)).strip()
    return hasil or None


def _angka(nilai: Any) -> float | None:
    if nilai is None or isinstance(nilai, bool):
        return None
    if isinstance(nilai, (int, float)):
        return float(nilai)
    try:
        return float(str(nilai).replace(",", "."))
    except ValueError:
        return None


def _baris(sheet: list[list[Any]]) -> list[dict[str, Any]]:
    if not sheet:
        raise DatasetTidakValid("Sheet sumber kosong")
    kepala = [str(item).strip() if item is not None else "" for item in sheet[0]]
    return [dict(zip(kepala, baris, strict=False)) for baris in sheet[1:]]


def _checksum_json(muatan: Any) -> str:
    serial = json.dumps(muatan, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serial.encode()).hexdigest()


def transformasi_sumber_database(isi: dict[str, Any]) -> dict[str, Any]:
    """Ubah ekspor workbook terklasifikasi menjadi bentuk tabel aplikasi.

    Kedua sheet digabung lewat `(Kategori, Kode Indikator)`, BUKAN lewat
    "ID Indikator". Penomoran IUP di sheet `Data Target-Realisasi` berbeda dari
    sheet `Basis Data Indikator`: dari 71 ID yang muncul di keduanya hanya 10
    (semuanya ISV) yang benar-benar indikator yang sama. Menggabungkan lewat ID
    menempelkan realisasi ke indikator yang salah tanpa galat apa pun — mis.
    "Harapan lama sekolah" menerima angka 73,5 milik "Usia Harapan Hidup".

    `(Kategori, Kode Indikator)` unik untuk seluruh 86 baris master dan
    memetakan seluruh baris nilai berkas nyata; kunci yang tidak dikenal
    menggagalkan transformasi, bukan dilewati diam-diam.
    """
    sheets = isi.get("sheets")
    if not isinstance(sheets, dict):
        raise DatasetTidakValid("Kunci 'sheets' tidak ditemukan")
    try:
        master = _baris(sheets["Basis Data Indikator"])
        sumber_nilai = _baris(sheets["Data Target-Realisasi"])
    except KeyError as exc:
        raise DatasetTidakValid(f"Sheet sumber tidak tersedia: {exc.args[0]}") from exc

    indikator: list[dict[str, Any]] = []
    metadata: list[dict[str, Any]] = []
    terlihat: set[str] = set()
    # (kategori, kode) -> id_indikator. Sheet nilai TIDAK boleh digabung lewat
    # "ID Indikator": kedua sheet memakai penomoran IUP yang berbeda, sehingga
    # ID yang sama menunjuk indikator yang berlainan. Lihat catatan di
    # `_indeks_kanonis` di bawah.
    indeks_kode: dict[tuple[str, str], str] = {}
    for baris in master:
        iid = _teks(baris.get("ID Indikator"))
        if not iid or not POLA_ID.fullmatch(iid):
            continue
        if iid in terlihat:
            continue
        terlihat.add(iid)
        kategori, nomor = iid.split("-", 1)
        kode_master = _teks(baris.get("Kode Indikator"))
        if kode_master:
            indeks_kode[(kategori, kode_master)] = iid
        klasifikasi = klasifikasi_kerangka(baris)
        indikator.append(
            {
                "id_indikator": iid,
                "kategori": kategori,
                "nomor": int(nomor),
                "kode_indikator": _teks(baris.get("Kode Indikator")),
                "nama_indikator": _teks(baris.get("Nama Indikator (RPJPD Provinsi / dipakai Kaltara)")),
                "kelompok": _teks(baris.get("Kelompok / Pilar")),
                "arah_pembangunan": _teks(baris.get("Arah Pembangunan")) if kategori == "ISV" else None,
                **klasifikasi,
                "satuan": None,
                "opd_pengampu": _teks(baris.get("Perangkat Daerah Pengampu (Kaltara)")),
                "sumber_data": _teks(baris.get("Sumber Data (RPJPD Provinsi)")),
                "frekuensi": _teks(baris.get("Frekuensi (RPJPD Provinsi)")),
                "status_metadata": _teks(baris.get("Status Metadata")),
                "status_ketersediaan": _teks(baris.get("Ketersediaan Data")),
                "periode_data": _teks(baris.get("Periode Data")),
                "tahun_terakhir": int(baris["Tahun Data Terakhir"])
                if _angka(baris.get("Tahun Data Terakhir"))
                else None,
                "is_proxy": (_teks(baris.get("Indikator Proxy?")) or "").casefold() in {"ya", "yes"},
                "catatan_teknis": _teks(baris.get("Catatan Kualitas Data")),
                "status_rpjmd": "MASUK_RPJMD",
                "sumber_master": _teks(isi.get("source")) or "dataset-database",
                "status_verifikasi": STATUS_DISETUJUI,
            }
        )
        metadata.append(
            {
                "id_indikator": iid,
                "definisi": _teks(baris.get("Definisi (RPJPD Provinsi)")),
                "rumus_mentah": _teks(baris.get("Rumus Perhitungan (RPJPD Provinsi)")),
                "interpretasi": _teks(baris.get("Interpretasi (RPJPD Provinsi)")),
                "sumber_data": _teks(baris.get("Sumber Data (RPJPD Provinsi)")),
                "frekuensi": _teks(baris.get("Frekuensi (RPJPD Provinsi)")),
                "status_metadata": _teks(baris.get("Status Metadata")),
                "sumber_metadata": "master-terklasifikasi",
            }
        )

    nilai: list[dict[str, Any]] = []
    kunci_nilai: set[tuple[str, int, str]] = set()
    tak_dikenal: set[tuple[str, str]] = set()
    for baris in sumber_nilai:
        if not _teks(baris.get("ID Indikator")):
            continue
        kunci_kode = (
            (_teks(baris.get("Kategori")) or "").upper(),
            _teks(baris.get("Kode Indikator")) or "",
        )
        iid = indeks_kode.get(kunci_kode)
        jenis = (_teks(baris.get("Jenis Nilai")) or "").casefold()
        tahun_angka = _angka(baris.get("Tahun"))
        if iid is None:
            tak_dikenal.add(kunci_kode)
            continue
        if jenis not in JENIS_NILAI or tahun_angka is None:
            continue
        tahun = int(tahun_angka)
        kunci = (iid, tahun, jenis)
        if kunci in kunci_nilai:
            raise DatasetTidakValid(f"Nilai tahunan duplikat: {iid}/{tahun}/{jenis}")
        kunci_nilai.add(kunci)
        nilai_angka = _angka(baris.get("Nilai (Angka)"))
        nilai_teks = _teks(baris.get("Nilai (Teks Asli)"))
        if nilai_angka is None and nilai_teks is None:
            continue
        nilai.append(
            {
                "id_indikator": iid,
                "wilayah_kode": KODE_PROVINSI,
                "tahun": tahun,
                "jenis": jenis,
                "periode": None,
                "nilai": nilai_angka,
                "nilai_teks": nilai_teks,
                "satuan_catatan": _teks(baris.get("Satuan/Catatan")),
                "sumber": _teks(isi.get("source")) or "dataset-database",
                "status_verifikasi": STATUS_DISETUJUI,
            }
        )

    if tak_dikenal:
        raise DatasetTidakValid(
            f"Baris nilai memakai (Kategori, Kode Indikator) yang tidak ada di sheet master: {sorted(tak_dikenal)[:10]}"
        )

    data = {"indikator": indikator, "metadata_indikator": metadata, "nilai_indikator": nilai}
    dataset = {
        "schema_version": VERSI_SKEMA,
        "dibuat_pada": datetime.now(UTC).isoformat(),
        "sumber": {"nama": _teks(isi.get("source")), "sha256": _checksum_json(isi)},
        "manifest": {nama: len(baris) for nama, baris in data.items()},
        "data": data,
    }
    dataset["checksum_data"] = _checksum_json(data)
    validasi_dataset(dataset)
    return dataset


def validasi_dataset(dataset: dict[str, Any]) -> None:
    """Validasi kontrak, integritas referensial, dan checksum dataset."""
    if dataset.get("schema_version") != VERSI_SKEMA:
        raise DatasetTidakValid(f"Versi dataset harus {VERSI_SKEMA}")
    data = dataset.get("data")
    if not isinstance(data, dict):
        raise DatasetTidakValid("Kunci data tidak tersedia")
    indikator = data.get("indikator", [])
    metadata = data.get("metadata_indikator", [])
    nilai = data.get("nilai_indikator", [])
    ids = [item.get("id_indikator") for item in indikator]
    # Master wajib lengkap; `nilai_indikator` sengaja TIDAK punya batas bawah
    # sehingga unggahan dengan sheet nilai parsial (bahkan kosong) tetap sah.
    # Aturan ini keputusan desain, bukan kelalaian — jangan "diperbaiki".
    if len(ids) != JUMLAH_INDIKATOR or len(set(ids)) != JUMLAH_INDIKATOR:
        raise DatasetTidakValid(f"Master harus berisi tepat {JUMLAH_INDIKATOR} ID unik")
    if any(not isinstance(iid, str) or not POLA_ID.fullmatch(iid) for iid in ids):
        raise DatasetTidakValid("Semua ID indikator wajib memakai pola ISV-001/IUP-001")
    if any(not item.get("nama_indikator") for item in indikator):
        raise DatasetTidakValid("Nama indikator tidak boleh kosong")
    himpunan = set(ids)
    if any(item.get("id_indikator") not in himpunan for item in metadata + nilai):
        raise DatasetTidakValid("Metadata/nilai mengacu pada indikator yang tidak dikenal")
    manifest = dataset.get("manifest", {})
    aktual = {"indikator": len(indikator), "metadata_indikator": len(metadata), "nilai_indikator": len(nilai)}
    if manifest != aktual:
        raise DatasetTidakValid("Jumlah pada manifest tidak sesuai isi dataset")
    if dataset.get("checksum_data") != _checksum_json(data):
        raise DatasetTidakValid("Checksum data dataset tidak sesuai")


def transformasi_workbook_excel(isi: bytes, nama: str) -> dict[str, Any]:
    """Byte `.xlsx` -> dataset tervalidasi. Titik masuk tunggal API dan CLI.

    Impor `excel` sengaja di dalam fungsi: modul itu mengimpor
    `DatasetTidakValid` dari sini, jadi impor tingkat modul akan melingkar.
    """
    from .excel import baca_workbook

    return transformasi_sumber_database(baca_workbook(isi, nama))


def muat_dataset(
    session: Session,
    dataset: dict[str, Any],
    *,
    lewati_nilai: set[tuple[str, str, int, str, int | None]] | None = None,
) -> dict[str, int]:
    """Upsert dataset ke skema aplikasi; pemanggil mengatur commit/rollback.

    `lewati_nilai` berisi kunci `(id_indikator, wilayah_kode, tahun, jenis,
    periode)` yang tidak boleh ditimpa — dipakai gerbang unggah untuk
    melindungi nilai hasil verifikasi operator. `None` (bawaan) berarti tidak
    ada yang dilindungi, sama seperti perilaku CLI sebelumnya.
    """
    from backend.app.models import Indikator, MetadataIndikator
    from backend.app.repositories import nilai as repo_nilai

    validasi_dataset(dataset)
    data = dataset["data"]
    berubah = {"indikator": 0, "metadata_indikator": 0, "nilai_indikator": 0, "nilai_dilewati": 0}
    for kolom in data["indikator"]:
        baris_indikator = session.get(Indikator, kolom["id_indikator"])
        if baris_indikator is None:
            baris_indikator = Indikator(
                id_indikator=kolom["id_indikator"],
                kategori=kolom["kategori"],
                nama_indikator=kolom["nama_indikator"],
            )
            session.add(baris_indikator)
        for nama, nilai in kolom.items():
            setattr(baris_indikator, nama, nilai)
        berubah["indikator"] += 1
    session.flush()
    for kolom in data["metadata_indikator"]:
        baris_metadata = session.get(MetadataIndikator, kolom["id_indikator"])
        if baris_metadata is None:
            baris_metadata = MetadataIndikator(id_indikator=kolom["id_indikator"])
            session.add(baris_metadata)
        for nama, nilai in kolom.items():
            setattr(baris_metadata, nama, nilai)
        berubah["metadata_indikator"] += 1
    for kolom in data["nilai_indikator"]:
        kunci = (
            kolom["id_indikator"],
            kolom["wilayah_kode"],
            kolom["tahun"],
            kolom["jenis"],
            kolom.get("periode"),
        )
        if lewati_nilai is not None and kunci in lewati_nilai:
            berubah["nilai_dilewati"] += 1
            continue
        repo_nilai.upsert(session, **kolom)
        berubah["nilai_indikator"] += 1
    return berubah


def baca_dataset(path: Path) -> dict[str, Any]:
    try:
        dataset = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DatasetTidakValid(f"Dataset tidak dapat dibaca: {exc}") from exc
    validasi_dataset(dataset)
    return dataset
