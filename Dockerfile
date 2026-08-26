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
# Entrypoint menjalankan migrasi Alembic (idempoten, dengan retry untuk race
# startup basis data di Coolify) sebelum server nyala — pola yang sama dengan
# deployment satu container lain. Seed akun tetap one-shot manual:
#   python -m backend.app.cli seed --tampilkan-sandi
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
# --proxy-headers: di balik proxy Coolify/Cloudflare, IP klien diambil dari
# X-Forwarded-For supaya pembatas laju login membatasi penyerang, bukan proxy.
# Daftar alamat terpercaya diatur lewat env FORWARDED_ALLOW_IPS (default
# 127.0.0.1, tidak memercayai header dari luar).
CMD ["python","-m","uvicorn","backend.app.main:app","--host","0.0.0.0","--port","8000","--proxy-headers"]
