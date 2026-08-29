# plans/

Rencana perbaikan hasil audit `/improve`. **Satu folder per pemanggilan**, agar batch tidak tercampur dan bisa dikerjakan nanti di harness lain.

Tidak perlu skill improve untuk mengeksekusi. Setiap folder batch mandiri: baca `AGENTS.md`, lalu ikuti README di dalam folder itu.

## Tata nama

```text
plans/improve-DD-MM-YYYY/
plans/improve-DD-MM-YYYY-2/   ← pemanggilan kedua pada tanggal yang sama
```

Contoh: `plans/improve-29-08-2026/` dibuat 29 Agustus 2026.

Jangan menaruh berkas plan di akar `plans/`. Plan seed/CRUD indikator yang sudah ada tetap di `docs/superpowers/plans/` — itu jalur produk terpisah.

## Daftar batch

| Folder | Tanggal | Commit acuan | Isi | Status |
|--------|---------|--------------|-----|--------|
| [improve-29-08-2026](improve-29-08-2026/README.md) | 29 Agustus 2026 | `8b3ae9a` | 001 usulan periode kosong; 002 unggahan ID master; 003 seri teramati; 004 ganti sandi awal; 005 katalog publik + periode | TODO |

Saat `/improve` dijalankan lagi: buat folder baru dengan tanggal hari itu, jangan menimpa folder lama. Tandai batch lama `STALE` di tabel ini hanya jika temuan sudah tidak berlaku (kode berubah jauh dari commit acuan).
