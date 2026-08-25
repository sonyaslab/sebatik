# Deploy Coolify + Cloudflare — sebatik.kaltarastats.id

Runbook memasang SEBATIK di home server dengan Coolify, dilayani lewat
Cloudflare untuk domain `sebatik.kaltarastats.id`. Ditujukan untuk pemasangan
pertama; pemasangan di server internal tanpa domain tetap mengikuti
[deploy-server-internal.md](deploy-server-internal.md).

## Arsitektur

```
Pengunjung ──HTTPS──> Cloudflare (DNS + proxy + WAF)
                         │  Full (strict)
                         ▼
                    Proxy Coolify (Traefik, sertifikat Let's Encrypt)
                         │  jaringan internal Docker
                         ▼
  ┌───────────────────────────────────────────────┐
  │ db (PostgreSQL 16) ─ migrasi (Alembic, sekali) │
  │ sebatik (FastAPI + frontend) ─ backup (pg_dump)│
  └───────────────────────────────────────────────┘
```

Port aplikasi terikat `127.0.0.1:8000` — satu-satunya jalur dari internet
adalah lewat proxy Coolify, sehingga tidak ada permintaan yang melewati
Cloudflare/Coolify dan memalsukan `X-Forwarded-For`.

## 1. Cloudflare

1. **DNS**: buat record `sebatik` (A ke IP publik rumah, atau CNAME ke tunnel
   bila memakai Cloudflare Tunnel), status **Proxied** (awan oranye).
   - IP publik dinamis? Gunakan Cloudflare Tunnel (`cloudflared`) dan *jangan*
     buka port router sama sekali; arahkan tunnel ke URL domain Coolify.
2. **SSL/TLS → Overview**: mode **Full (strict)**. Jangan "Flexible" — itu
   menurunkan ke HTTP ke asal dan merusak cookie `secure`.
3. **SSL/TLS → Edge Certificates**: aktifkan *Always Use HTTPS* dan HSTS.
4. **Security → WAF → Rate limiting** (disarankan): aturan untuk
   `/api/v1/auth/login`, misalnya 10 permintaan/menit/IP. Ini lapisan luar
   pembatas laju bawaan aplikasi (5 gagal/menit per IP+nama pengguna).

## 2. Coolify

1. **New Resource → Docker Compose**, dari repositori GitHub
   `bpsprovkaltara/sebatik`, branch `main`. Coolify membaca
   `docker-compose.yml` apa adanya: `db`, `migrasi` (berjalan sekali lalu
   keluar), `sebatik`, `backup`.
   Sudah punya PostgreSQL sendiri di server? Lanjut ke §5 dan pakai
   `docker-compose.coolify.yml` — jangan ikut langkah env `POSTGRES_PASSWORD`
   di bawah.
2. **Environment variables** (UI Coolify; jangan commit `.env`): salin isi
   `.env.production.example` lalu isi:
   - `POSTGRES_PASSWORD` — sandi kuat untuk PostgreSQL.
   - `SEBATIK_SECRET_KEY` — acak minimal 32 karakter (`openssl rand -hex 32`).
     Aplikasi **menolak menyala** bila masih nilai contoh.
   - `SEBATIK_DATABASE_URL` — ganti `GANTI-SANDI` dengan nilai
     `POSTGRES_PASSWORD` yang sama.
   - `FORWARDED_ALLOW_IPS=*` — aman karena port aplikasi hanya di localhost.
3. **Domain**: pada service `sebatik`, isi `https://sebatik.kaltarastats.id`.
   Coolify meminta sertifikat Let's Encrypt lewat HTTP-01; lewat proxy
   Cloudflare challenge tetap sampai ke asal selama SSL mode Full (strict).
   Bila gagal, pakai DNS-01 dengan Cloudflare API token (lihat dokumentasi
   Coolify "Let's Encrypt with DNS challenge").
4. **Deploy**. Layanan `migrasi` harus berstatus exited(0); `sebatik` sehat.

## 3. Data awal

Skema dibuat Alembic (service `migrasi`), tetapi akun awal dibuat eksplisit:

```bash
docker compose run --rm sebatik python -m backend.app.cli seed --tampilkan-sandi
```

Sandi dicetak **sekali** — catat dan bagikan lewat kanal aman; semua akun awal
wajib mengganti sandi saat login pertama. Untuk memindahkan isi pemasangan
SQLite lama, lihat "Pindah ke PostgreSQL" di [README.md](README.md).

## 4. Verifikasi pasca-deploy

```bash
curl -s https://sebatik.kaltarastats.id/api/v1/health        # {"status":"ok"}
curl -sI https://sebatik.kaltarastats.id | head -1           # HTTP/2 200 via Cloudflare
docker compose logs sebatik --tail 20                        # tidak ada galat
```

- Masuk sebagai admin, ganti sandi, periksa bilah beranda memuat data.
- Unggah satu usulan dengan bukti (menguji volume `sebatik_data`).
- Besoknya: `docker compose exec backup ls -lt /backup | head` — dump harian
  sudah tercipta.

## 5. Varian: memakai PostgreSQL yang sudah berjalan

Bila home server sudah menjalankan PostgreSQL, SEBATIK tidak membuat instance
baru. Yang berubah hanya tiga hal:

1. **Berkas compose**: arahkan sumber Coolify ke `docker-compose.coolify.yml`
   (atau tempel isinya ke penyusun compose). Varian ini tidak punya service
   `db` dan `backup` — pencadangan mengikuti kebijakan instance yang sudah ada.
2. **Basis data**: siapkan sekali di instance yang sudah berjalan
   (nama database dan pengguna bebas, contoh memakai `sebatik`):

   ```sql
   CREATE ROLE sebatik LOGIN PASSWORD 'SANDI_KUAT';
   CREATE DATABASE sebatik OWNER sebatik;
   ```

3. **Variabel lingkungan**: salin `.env.coolify.example`. Perbedaannya
   hanya `SEBATIK_DATABASE_URL` menunjuk ke instance tersebut dan tidak ada
   `POSTGRES_PASSWORD`. Host yang dipakai tergantung letak instance —
   penjelasannya ada di komentar berkas contoh itu (host langsung, container
   lain, atau mesin terpisah).

Alembic tetap dijalankan service `migrasi` sebelum aplikasi menyala; CI menguji
migrasi pada PostgreSQL 16, jadi versi instance lain belum teruji.

## 6. Operasional

- **Backup**: `pg_dump` harian, retensi 30, di volume `sebatik_backup`.
  Volume itu hanya hidup di home server — replikasi keluar (rclone/rsync ke
  penyimpanan awan) masih menjadi tugas manual.
- **Pembaruan**: push ke `main` → Coolify build ulang; `migrasi` menjalankan
  Alembic `upgrade head` sebelum `sebatik` berganti container.
- **Rollback aplikasi**: deploy ulang commit lama dari UI Coolify. Rollback
  skema: `python -m alembic -c backend/alembic.ini downgrade -1` dari
  container migrasi (setiap migrasi punya turunan; diuji di CI).
- **Kunci rahasia**: rotasi `SEBATIK_SECRET_KEY` dengan mengisi kunci lama di
  `SEBATIK_SECRET_KEYS` (dipisah koma) agar sesi berjalan tidak terputus
  serentak; kosongkan kembali setelah 24 jam (umur token segar).
