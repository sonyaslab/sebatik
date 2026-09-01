"""Dukung nilai teks pada usulan operator.

Revision ID: 0005_nilai_teks_usulan
Revises: 0004_klasifikasi_makro
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_nilai_teks_usulan"
down_revision: str | Sequence[str] | None = "0004_klasifikasi_makro"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("usulan_nilai") as batch:
        batch.alter_column("nilai", existing_type=sa.Numeric(20, 6), nullable=True)
        batch.add_column(sa.Column("nilai_teks", sa.Text(), nullable=True))
        batch.add_column(sa.Column("batch_id", sa.String(length=32), nullable=True))
        batch.create_check_constraint(
            "ck_usulan_tepat_satu_nilai",
            "(nilai IS NOT NULL AND nilai_teks IS NULL) OR (nilai IS NULL AND nilai_teks IS NOT NULL)",
        )
        batch.create_index("ix_usulan_batch", ["batch_id"], unique=False)


def downgrade() -> None:
    op.execute(sa.text("UPDATE usulan_nilai SET nilai = 0 WHERE nilai IS NULL"))
    with op.batch_alter_table("usulan_nilai") as batch:
        batch.drop_index("ix_usulan_batch")
        batch.drop_constraint("ck_usulan_tepat_satu_nilai", type_="check")
        batch.drop_column("batch_id")
        batch.drop_column("nilai_teks")
        batch.alter_column("nilai", existing_type=sa.Numeric(20, 6), nullable=False)
