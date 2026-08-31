"""Isi klasifikasi makro dari master data indikator.

Revision ID: 0004_klasifikasi_makro
Revises: 0003_kode_sdgs_text
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0004_klasifikasi_makro"
down_revision: str | Sequence[str] | None = "0003_kode_sdgs_text"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KELOMPOK_MAKRO: dict[str, tuple[str, ...]] = {
    "Makro - Ekonomi": (
        "ISV-001",
        "ISV-003",
        "ISV-006",
        "IUP-017",
        "IUP-018",
        "IUP-019",
        "IUP-020",
        "IUP-036",
        "IUP-037",
    ),
    "Makro - Sosial & Ketenagakerjaan": (
        "ISV-004",
        "ISV-005",
        "IUP-014",
        "IUP-028",
        "IUP-029",
        "IUP-030",
    ),
    "Makro - Harga": ("IUP-035", "IUP-050"),
    "Makro - Fiskal & Keuangan": ("IUP-049", "IUP-052", "IUP-053", "IUP-055"),
}


def upgrade() -> None:
    koneksi = op.get_bind()
    # Semua indikator yang belum diklasifikasikan dibuat eksplisit agar data
    # lama sama lengkapnya dengan workbook/fixture baru. Nilai admin yang
    # sudah ada tidak disentuh, kecuali 21 ID makro kanonis di bawah.
    koneksi.execute(sa.text("UPDATE indikator SET kelompok_makro = 'Non-Makro' WHERE kelompok_makro IS NULL"))
    for kelompok, daftar_id in KELOMPOK_MAKRO.items():
        koneksi.execute(
            sa.text("UPDATE indikator SET kelompok_makro = :kelompok WHERE id_indikator IN :daftar_id").bindparams(
                sa.bindparam("daftar_id", expanding=True)
            ),
            {"kelompok": kelompok, "daftar_id": daftar_id},
        )


def downgrade() -> None:
    semua_id = tuple(id_indikator for daftar_id in KELOMPOK_MAKRO.values() for id_indikator in daftar_id)
    koneksi = op.get_bind()
    koneksi.execute(
        sa.text("UPDATE indikator SET kelompok_makro = NULL WHERE id_indikator IN :daftar_id").bindparams(
            sa.bindparam("daftar_id", expanding=True)
        ),
        {"daftar_id": semua_id},
    )
    koneksi.execute(sa.text("UPDATE indikator SET kelompok_makro = NULL WHERE kelompok_makro = 'Non-Makro'"))
