#!/bin/sh
# Jalankan migrasi skema sekali di awal, lalu serahkan ke CMD (uvicorn).
# Variabel lingkungan (SEBATIK_DATABASE_URL dsb.) disuntikkan Coolify/docker
# lewat -e; backend/alembic/env.py membacanya lewat Settings.
set -e

cd /app

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
