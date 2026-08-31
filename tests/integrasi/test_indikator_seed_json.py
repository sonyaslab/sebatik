"""Tes kewarasan fixture backend/app/data/indikator_seed.json yang di-commit.

Ini bukan tes logic — filenya sudah statis. Tesnya menjaga fixture tidak
diam-diam rusak (duplikat PK, id_indikator salah format, dsb) di commit
berikutnya tanpa lewat scripts/ekspor_seed_indikator.py lagi.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

BERKAS = Path(__file__).resolve().parents[2] / "backend" / "app" / "data" / "indikator_seed.json"
POLA_ID = re.compile(r"^(ISV|IUP)-\d{3}$")


def _muatan() -> dict:
    return json.loads(BERKAS.read_text(encoding="utf-8"))


def test_berkas_ada():
    assert BERKAS.exists(), f"{BERKAS} belum digenerate — jalankan scripts/ekspor_seed_indikator.py"


def test_delapan_puluh_enam_indikator():
    muatan = _muatan()
    assert len(muatan["indikator"]) == 86


def test_setiap_id_indikator_format_tiga_digit():
    for baris in _muatan()["indikator"]:
        assert POLA_ID.match(baris["id_indikator"]), baris["id_indikator"]


def test_tidak_ada_id_indikator_duplikat():
    ids = [baris["id_indikator"] for baris in _muatan()["indikator"]]
    assert len(ids) == len(set(ids))


def test_setiap_indikator_punya_baris_metadata_pasangan():
    muatan = _muatan()
    ids_indikator = {baris["id_indikator"] for baris in muatan["indikator"]}
    ids_metadata = {baris["id_indikator"] for baris in muatan["metadata_indikator"]}
    assert ids_indikator == ids_metadata


def test_nilai_wilayah_selalu_provinsi_dan_jenis_valid():
    for baris in _muatan()["nilai_indikator"]:
        assert baris["wilayah_kode"] == "65"
        assert baris["jenis"] in ("realisasi", "target")


def test_nilai_id_indikator_semuanya_dikenal():
    muatan = _muatan()
    ids_indikator = {baris["id_indikator"] for baris in muatan["indikator"]}
    for baris in muatan["nilai_indikator"]:
        assert baris["id_indikator"] in ids_indikator


def test_tidak_ada_duplikat_kunci_nilai():
    kunci = [(b["id_indikator"], b["tahun"], b["jenis"]) for b in _muatan()["nilai_indikator"]]
    assert len(kunci) == len(set(kunci))


def test_klasifikasi_makro_fixture_lengkap_dan_berjumlah_dua_puluh_satu():
    indikator = _muatan()["indikator"]
    assert all(baris.get("kelompok_makro") for baris in indikator)
    makro = [baris for baris in indikator if baris["kelompok_makro"].startswith("Makro")]
    assert len(makro) == 21
    assert {baris["id_indikator"] for baris in makro} >= {
        "ISV-001",
        "ISV-004",
        "ISV-005",
        "IUP-028",
        "IUP-050",
    }
