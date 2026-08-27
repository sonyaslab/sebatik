"""Unggahan Excel indikator: validasi, diff, dan penerapan setelah disetujui.

Alurnya sengaja dua langkah. Admin mengunggah `.xlsx`, server mengarsipkan
berkasnya lalu menyusun pratinjau perubahan; pemuatan ke basis data baru
terjadi setelah persetujuan eksplisit.

Konversi Excel dilakukan di `src/etl/excel.py` dan hasilnya tetap wajib lolos
`validasi_dataset()` — yang berpindah hanyalah tempat konversi, bukan
ketatnya pemeriksaan.

Nilai yang berasal dari alur verifikasi operator (`usulan_id` terisi)
dilindungi: baris seperti itu dilaporkan sebagai konflik di pratinjau dan
tidak pernah ditimpa unggahan massal.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

from sqlalchemy.orm import Session

from ..config import settings
from ..models import KODE_PROVINSI, StatusUnggahan
from ..repositories import nilai as repo_nilai
from ..repositories import tata_kelola as repo_tata_kelola

# Kunci nilai tahunan provinsi sebagaimana dipakai diff: (id, tahun, jenis).
KunciNilai = tuple[str, int, str]


class BerkasTidakValid(Exception):
    """Berkas unggahan tidak memenuhi syarat untuk diproses."""


class HasilPratinjau(NamedTuple):
    path_arsip: Path
    path_staging: Path
    diff: dict[str, Any]


def berekstensi_excel(nama_berkas: str | None) -> bool:
    return bool(nama_berkas) and str(nama_berkas).lower().endswith(".xlsx")


def berekstensi_xls_lama(nama_berkas: str | None) -> bool:
    """`.xls` biner lama; openpyxl tidak membacanya, jadi pesannya dibedakan."""
    return bool(nama_berkas) and str(nama_berkas).lower().endswith(".xls")


def ukuran_wajar(jumlah_byte: int) -> bool:
    return jumlah_byte <= settings.max_unggah_bytes


def arsipkan(isi: bytes) -> Path:
    direktori = Path(settings.archive_dir)
    direktori.mkdir(parents=True, exist_ok=True)
    berkas = direktori / f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid.uuid4()}.xlsx"
    berkas.write_bytes(isi)
    return berkas


def _dataset_dari_arsip(path: Path, nama_asli: str | None = None) -> dict[str, Any]:
    """Baca ulang berkas arsip `.xlsx` menjadi dataset tervalidasi.

    Pratinjau dan penerapan sama-sama mem-parsing ulang berkas yang sama.
    Untuk 86 + ~660 baris biayanya milidetik, dan cara ini menghindari
    penambahan kolom baru di tabel `unggahan_excel` (tanpa migrasi).

    `nama_asli` dipakai sebagai provenance (`sumber_master`/`sumber`) supaya
    yang tercatat adalah nama berkas yang diunggah admin, bukan nama arsip
    ber-UUID di disk.
    """
    from src.etl.database import DatasetTidakValid, transformasi_workbook_excel

    try:
        return transformasi_workbook_excel(path.read_bytes(), nama_asli or path.name)
    except DatasetTidakValid as exc:
        raise BerkasTidakValid(str(exc)) from exc
    except OSError as exc:
        raise BerkasTidakValid(f"Arsip unggahan tidak dapat dibaca: {exc}") from exc


def _ringkas_dataset(dataset: dict[str, Any]) -> tuple[dict[str, str], dict[KunciNilai, float | None]]:
    data = dataset["data"]
    indikator = {baris["id_indikator"]: baris["nama_indikator"] for baris in data["indikator"]}
    nilai = {
        (baris["id_indikator"], baris["tahun"], baris["jenis"]): baris["nilai"]
        for baris in data["nilai_indikator"]
        if baris.get("wilayah_kode") == KODE_PROVINSI and baris.get("periode") is None
    }
    return indikator, nilai


def _konflik(
    session: Session, nilai_baru: dict[KunciNilai, float | None]
) -> dict[KunciNilai, tuple[float | None, int | None]]:
    """Baris hasil verifikasi yang nilainya akan berubah bila unggahan dimuat.

    `semua_nilai_provinsi()` sudah mengembalikan objek `NilaiIndikator` utuh,
    jadi `usulan_id` terbaca tanpa query tambahan.
    """
    hasil: dict[KunciNilai, tuple[float | None, int | None]] = {}
    for baris in repo_nilai.semua_nilai_provinsi(session):
        if baris.usulan_id is None:
            continue
        kunci = (baris.id_indikator, baris.tahun, baris.jenis)
        if kunci not in nilai_baru or nilai_baru[kunci] == baris.nilai:
            continue
        hasil[kunci] = (baris.nilai, baris.usulan_id)
    return hasil


def _lewati_dari_konflik(konflik: dict[KunciNilai, tuple[float | None, int | None]]) -> set[tuple[Any, ...]]:
    """Kunci lima unsur sesuai kontrak `muat_dataset(lewati_nilai=...)`."""
    return {(id_indikator, KODE_PROVINSI, tahun, jenis, None) for id_indikator, tahun, jenis in konflik}


def susun_diff(
    session: Session, path_staging: Path, nama_asli: str | None = None
) -> tuple[dict[str, Any], dict[KunciNilai, tuple[float | None, int | None]]]:
    """Bandingkan dataset unggahan dengan nilai provinsi yang berlaku."""
    dataset = _dataset_dari_arsip(path_staging, nama_asli)
    indikator_baru, nilai_baru = _ringkas_dataset(dataset)
    indikator_lama = {item.id_indikator: item.nama_indikator for item in repo_nilai.semua_indikator_ringkas(session)}
    nilai_lama = {
        (baris.id_indikator, baris.tahun, baris.jenis): baris.nilai
        for baris in repo_nilai.semua_nilai_provinsi(session)
    }
    konflik = _konflik(session, nilai_baru)

    berubah = [
        {
            "id": kunci[0],
            "tahun": kunci[1],
            "jenis": kunci[2],
            "lama": nilai_lama.get(kunci),
            "baru": nilai_baru.get(kunci),
        }
        for kunci in sorted(set(nilai_lama) | set(nilai_baru))
        if nilai_lama.get(kunci) != nilai_baru.get(kunci) and kunci not in konflik
    ]
    dilindungi = [
        {
            "id": kunci[0],
            "tahun": kunci[1],
            "jenis": kunci[2],
            "lama": konflik[kunci][0],
            "baru": nilai_baru.get(kunci),
            "usulan_id": konflik[kunci][1],
        }
        for kunci in sorted(konflik)
    ]
    diff = {
        "indikator_baru": sorted(set(indikator_baru) - set(indikator_lama)),
        "indikator_hilang": sorted(set(indikator_lama) - set(indikator_baru)),
        "nilai_berubah": berubah,
        "nilai_konflik": dilindungi,
        "ringkasan": {
            "indikator": len(indikator_baru),
            "nilai_dimuat": len(nilai_baru) - len(konflik),
            "nilai_dilindungi": len(konflik),
        },
    }
    return diff, konflik


def terapkan(session: Session, unggahan: Any, pengguna_id: int | None) -> int:
    """Muat dimensi, metadata, dan fakta dari unggahan dalam transaksi persetujuan."""
    path_staging = Path(unggahan.path_arsip)
    if not path_staging.exists():
        raise BerkasTidakValid("Berkas unggahan tidak ditemukan")

    from src.etl.database import muat_dataset

    dataset = _dataset_dari_arsip(path_staging, unggahan.nama_file_asli)
    _, nilai_baru = _ringkas_dataset(dataset)
    nilai_lama = {
        (baris.id_indikator, baris.tahun, baris.jenis): baris.nilai
        for baris in repo_nilai.semua_nilai_provinsi(session)
    }
    # Dihitung ulang, bukan dibaca dari ringkasan_diff yang tersimpan: basis
    # data bisa berubah antara pratinjau dan persetujuan.
    konflik = _konflik(session, nilai_baru)

    hasil = muat_dataset(session, dataset, lewati_nilai=_lewati_dari_konflik(konflik))

    for kunci, nilai in nilai_baru.items():
        if kunci in konflik:
            continue
        lama = nilai_lama.get(kunci)
        if lama == nilai:
            continue
        id_indikator, tahun, jenis = kunci
        repo_tata_kelola.catat_perubahan(
            session,
            pengguna_id=pengguna_id,
            id_indikator=id_indikator,
            field=f"nilai:{tahun}:{jenis}",
            nilai_lama=None if lama is None else str(lama),
            nilai_baru=str(nilai),
            sumber_perubahan="unggah",
            referensi_id=str(unggahan.id),
        )

    repo_tata_kelola.catat_aktivitas(
        session,
        pengguna_id=pengguna_id,
        aksi="unggahan_disetujui",
        objek_tipe="unggahan_excel",
        objek_id=str(unggahan.id),
        detail={
            "nilai_dimuat": hasil["nilai_indikator"],
            "nilai_dilindungi": hasil["nilai_dilewati"],
        },
    )

    # Ringkasan diff yang tersimpan ditimpa dengan angka yang BENAR-BENAR
    # diterapkan. Kolomnya sudah ada (TEXT), jadi log riwayat bisa menampilkan
    # hasil nyata tanpa perlu migrasi kolom baru.
    unggahan.ringkasan_diff = ringkasan_diff_json(
        {
            **json.loads(unggahan.ringkasan_diff or "{}"),
            "diterapkan": {
                "indikator": hasil["indikator"],
                "nilai_dimuat": hasil["nilai_indikator"],
                "nilai_dilindungi": hasil["nilai_dilewati"],
            },
        }
    )
    unggahan.status = StatusUnggahan.DISETUJUI
    unggahan.disetujui_pada = datetime.now(UTC)
    return hasil["nilai_indikator"]


def _baris_riwayat(baris: Any, username: str | None) -> dict[str, Any]:
    """Satu baris log: waktu unggah, waktu penerapan, dan apa yang berubah.

    Angka diambil dari blok `diterapkan` yang ditulis `terapkan()`; selama
    unggahan belum disetujui, blok itu belum ada dan angkanya None.
    """
    try:
        ringkasan = json.loads(baris.ringkasan_diff or "{}")
    except ValueError:
        ringkasan = {}
    diterapkan = ringkasan.get("diterapkan") or {}
    return {
        "id": baris.id,
        "nama_file_asli": baris.nama_file_asli,
        "status": baris.status,
        "diunggah_pada": baris.dibuat_pada,
        "diterapkan_pada": baris.disetujui_pada,
        "nilai_dimuat": diterapkan.get("nilai_dimuat"),
        "nilai_dilindungi": diterapkan.get("nilai_dilindungi"),
        "indikator_baru": diterapkan.get("indikator"),
        "oleh": username,
    }


def riwayat(session: Session, batas: int = 10) -> dict[str, Any]:
    """Muatan `GET /admin/unggah` — perakitan bentuk respons ada di sini, bukan router."""
    return {
        "data": [
            _baris_riwayat(baris, username) for baris, username in repo_tata_kelola.daftar_unggahan(session, batas)
        ]
    }


def ringkasan_diff_json(diff: dict[str, Any]) -> str:
    return json.dumps(diff, ensure_ascii=False)
