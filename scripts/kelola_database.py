"""Transformasi, validasi, dan pemuatan dataset database SEBATIK."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.etl.database import DatasetTidakValid, baca_dataset, muat_dataset, transformasi_sumber_database  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="perintah", required=True)
    transformasi = sub.add_parser("transformasi", help="ubah JSON sumber menjadi dataset database")
    transformasi.add_argument("sumber", type=Path)
    transformasi.add_argument("keluaran", type=Path)
    validasi = sub.add_parser("validasi", help="validasi dataset tanpa menulis database")
    validasi.add_argument("dataset", type=Path)
    muat = sub.add_parser("muat", help="muat dataset ke skema aplikasi")
    muat.add_argument("dataset", type=Path)
    muat.add_argument("--database-url", default=None, help="bawaan: SEBATIK_DATABASE_URL")
    args = parser.parse_args()
    try:
        if args.perintah == "transformasi":
            sumber = json.loads(args.sumber.read_text(encoding="utf-8"))
            dataset = transformasi_sumber_database(sumber)
            args.keluaran.parent.mkdir(parents=True, exist_ok=True)
            args.keluaran.write_text(json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Dataset dibuat: {args.keluaran}; manifest={dataset['manifest']}")
            return 0
        dataset = baca_dataset(args.dataset)
        if args.perintah == "validasi":
            print(f"Dataset valid: {dataset['checksum_data']}; manifest={dataset['manifest']}")
            return 0
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from backend.app.config import settings

        mesin = create_engine(args.database_url or settings.database_url, pool_pre_ping=True)
        with Session(mesin) as session, session.begin():
            hasil = muat_dataset(session, dataset)
        mesin.dispose()
        print(f"Dataset dimuat dalam satu transaksi: {hasil}")
        return 0
    except (OSError, json.JSONDecodeError, DatasetTidakValid) as exc:
        print(f"ETL gagal: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


