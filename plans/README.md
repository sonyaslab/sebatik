# plans/

Rencana perbaikan hasil audit `/improve`. **Satu folder per pemanggilan**, agar batch tidak tercampur dan bisa dikerjakan nanti di harness lain.

Tidak perlu skill improve untuk mengeksekusi. Setiap folder batch mandiri: baca `AGENTS.md`, lalu ikuti README di dalam folder itu.

## Tata nama

```text
plans/improve-DD-MM-YYYY/
plans/improve-DD-MM-YYYY-2/   ← pemanggilan kedua pada tanggal yang sama
```

Contoh: `plans/improve-29-08-2026/` dibuat 29 Agustus 2026.

Jangan menaruh berkas plan di akar `plans/`. Plan seed/CRUD indikator yang sudah ada tetap di `docs/superpowers/plans/` — itu jalur produk terpisah (sudah diimplementasikan di `main`).

## Daftar batch

| Folder | Tanggal | Commit acuan | Isi | Status |
|--------|---------|--------------|-----|--------|
| [improve-29-08-2026](improve-29-08-2026/README.md) | 29 Agustus 2026 | awal `8b3ae9a`, disesuaikan `4a7939f` | 001 usulan periode kosong (TODO); 002 unggahan ID master (**DITOLAK**, sudah diperbaiki jalur Excel); 003 seri teramati (TODO); 004 ganti sandi awal (TODO); 005 katalog publik + periode (TODO) | 4 TODO, 1 DITOLAK |

Saat `/improve` dijalankan lagi: buat folder baru dengan tanggal hari itu, jangan menimpa folder lama. Tandai batch lama `STALE` di tabel ini hanya jika temuan sudah tidak berlaku (kode berubah jauh dari commit acuan).
