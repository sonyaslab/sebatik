"""Unggahan dataset database: validasi, diff, dan penerapan setelah disetujui.

Alurnya sengaja dua langkah. Transformasi sumber dilakukan di luar proses API;
server hanya memvalidasi dataset, membandingkannya, lalu memuat setelah disetujui.
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


class BerkasTidakValid(Exception):
    """Berkas unggahan tidak memenuhi syarat untuk diproses."""


class HasilPratinjau(NamedTuple):
    path_arsip: Path
    path_staging: Path
    diff: dict[str, Any]


def berekstensi_database(nama_berkas: str | None) -> bool:
    return bool(nama_berkas) and str(nama_berkas).lower().endswith(".json")


def ukuran_wajar(jumlah_byte: int) -> bool:
    return jumlah_byte <= settings.max_unggah_bytes


def arsipkan(isi: bytes) -> Path:
    direktori = Path(settings.archive_dir)
    direktori.mkdir(parents=True, exist_ok=True)
    berkas = direktori / f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid.uuid4()}.database.json"
    berkas.write_bytes(isi)
    return berkas


def _baca_dataset(path: Path) -> tuple[dict[str, str], dict[tuple[str, int, str], float | None]]:
    from src.etl.database import DatasetTidakValid, baca_dataset

    try:
        dataset = baca_dataset(path)
    except DatasetTidakValid as exc:
        raise BerkasTidakValid(str(exc)) from exc
    data = dataset["data"]
    indikator = {baris["id_indikator"]: baris["nama_indikator"] for baris in data["indikator"]}
    nilai = {
        (baris["id_indikator"], baris["tahun"], baris["jenis"]): baris["nilai"]
        for baris in data["nilai_indikator"]
        if baris.get("wilayah_kode") == KODE_PROVINSI and baris.get("periode") is None
    }
    return indikator, nilai


def susun_diff(
    session: Session, path_staging: Path
) -> tuple[dict[str, Any], dict[tuple[str, int, str], tuple[float | None, str | None]]]:
    """Bandingkan dataset database dengan nilai provinsi yang berlaku."""
    indikator_baru, nilai_baru = _baca_dataset(path_staging)
    indikator_lama = {item.id_indikator: item.nama_indikator for item in repo_nilai.semua_indikator_ringkas(session)}
    nilai_lama = {
        (baris.id_indikator, baris.tahun, baris.jenis): baris.nilai
        for baris in repo_nilai.semua_nilai_provinsi(session)
    }
    diff = {
        "indikator_baru": sorted(set(indikator_baru) - set(indikator_lama)),
        "indikator_hilang": sorted(set(indikator_lama) - set(indikator_baru)),
        "nilai_berubah": [
            {
                "id": kunci[0],
                "tahun": kunci[1],
                "jenis": kunci[2],
                "lama": nilai_lama.get(kunci),
                "baru": nilai_baru.get(kunci),
            }
            for kunci in sorted(set(nilai_lama) | set(nilai_baru))
            if nilai_lama.get(kunci) != nilai_baru.get(kunci)
        ],
    }
    return diff, {}


def terapkan(session: Session, unggahan: Any, pengguna_id: int | None) -> int:
    """Muat dimensi, metadata, dan fakta dari dataset dalam transaksi persetujuan."""
    path_staging = Path(unggahan.path_arsip)
    if not path_staging.exists():
        raise BerkasTidakValid("Dataset database tidak ditemukan")

    from src.etl.database import baca_dataset, muat_dataset

    dataset = baca_dataset(path_staging)
    _, nilai_baru = _baca_dataset(path_staging)
    nilai_lama = {
        (baris.id_indikator, baris.tahun, baris.jenis): baris.nilai
        for baris in repo_nilai.semua_nilai_provinsi(session)
    }
    hasil = muat_dataset(session, dataset)
    for (id_indikator, tahun, jenis), nilai in nilai_baru.items():
        lama = nilai_lama.get((id_indikator, tahun, jenis))
        if lama == nilai:
            continue
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

    unggahan.status = StatusUnggahan.DISETUJUI
    unggahan.disetujui_pada = datetime.now(UTC)
    return hasil["nilai_indikator"]


def ringkasan_diff_json(diff: dict[str, Any]) -> str:
    return json.dumps(diff, ensure_ascii=False)
