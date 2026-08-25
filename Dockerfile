FROM node:22-alpine AS frontend
WORKDIR /build
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY src src
COPY scripts scripts
COPY --from=frontend /build/dist frontend/dist
# Direktori data dibuat kosong. Isinya tidak ikut ke dalam image: basis data
# tinggal di PostgreSQL (volume terpisah), sedangkan arsip unggahan dan bukti
# dukung dipasang sebagai volume supaya tidak hilang saat image diganti.
RUN mkdir -p /app/data/processed/arsip-unggahan /app/data/processed/bukti-dukung /app/backup
EXPOSE 8000
# Migrasi skema berjalan sebelum server: deployment satu container
# (aplikasi Dockerfile di Coolify) tidak punya service migrasi terpisah.
# alembic upgrade head idempoten — tidak melakukan apa-apa saat skema
# sudah mutakhir, sehingga aman diulang tiap restart.
# --proxy-headers: di balik proxy Coolify/Cloudflare, IP klien diambil dari
# X-Forwarded-For supaya pembatas laju login membatasi penyerang, bukan proxy.
# Daftar alamat terpercaya diatur lewat env FORWARDED_ALLOW_IPS (default
# 127.0.0.1, tidak memercayai header dari luar).
CMD ["sh","-c","python -m alembic -c backend/alembic.ini upgrade head && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
