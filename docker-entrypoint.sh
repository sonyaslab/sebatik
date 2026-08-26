#!/bin/sh
# Jalankan migrasi skema sekali di awal, lalu serahkan ke CMD (uvicorn).
# Variabel lingkungan (SEBATIK_DATABASE_URL dsb.) disuntikkan Coolify/docker
# lewat -e; backend/alembic/env.py membacanya lewat Settings.
set -e

cd /app

# Galat format URL tidak akan sembuh dengan diulang; periksa sekali di awal
# supaya pesannya jelas dan sandi tetap tersamar, bukan 10 percobaan sia-sia.
python - <<'PY' || exit 1
import os
from sqlalchemy.engine import make_url

url = os.environ.get("SEBATIK_DATABASE_URL", "")
try:
    u = make_url(url)
    print(f"[entrypoint] URL valid: {u.drivername} -> {u.host}:{u.port}/{u.database}")
except Exception as e:
    print(f"[entrypoint] SEBATIK_DATABASE_URL TIDAK VALID: {e}")
    print("[entrypoint] periksa: prefix postgresql+psycopg:// ; sandi ter-encode")
    print("[entrypoint] (%40 untuk @, %3A untuk :, %25 untuk %) ; tanpa tanda kutip.")
    # Tampilkan bentuk mentah yang diterima container (sandi disamarkan):
    # spasi/newline senyap hasil salin-tempel terlihat di sini.
    if url:
        tampil = url.split(":", 1)[0] + ":***@" + (url.rsplit("@", 1)[1] if "@" in url else "?")
        print(f"[entrypoint] repr mentah (panjang {len(url)}): {tampil!r}")
    else:
        print("[entrypoint] nilai kosong / variabel tidak sampai ke container")
    raise SystemExit(1)
PY

# Basis data bisa belum terjangkau detik pertama container menyala (race
# startup di Coolify/compose). Coba berkali-kali sebelum menyerah.
attempts=10
i=1
while [ "$i" -le "$attempts" ]; do
  echo "[entrypoint] alembic upgrade head (percobaan $i/$attempts)..."
  if python -m alembic -c backend/alembic.ini upgrade head; then
    echo "[entrypoint] skema mutakhir."
    break
  fi
  if [ "$i" -eq "$attempts" ]; then
    echo "[entrypoint] migrasi gagal setelah $attempts percobaan — berhenti." >&2
    exit 1
  fi
  i=$((i + 1))
  sleep 3
done

echo "[entrypoint] menjalankan server."
exec "$@"
