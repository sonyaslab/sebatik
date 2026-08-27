"""Kontrak endpoint CRUD admin /api/v1/admin/indikator.

Memakai id "ISV-999" — sengaja dipilih supaya tidak bentrok dengan fixture
_isi_benih() (ISV-001, ISV-002, ISV-005, IUP-001, IUP-002) di conftest.py.

Urutan tes di berkas ini berarti: fixture `client`/`db_uji` ber-scope session,
jadi satu basis data dipakai bersama seluruh tes di tests/api/. Tes di bawah
ditulis untuk berjalan berurutan (buat -> baca -> ubah -> hapus). Jangan
diacak atau disisipi tes lain di tengahnya.
"""

from __future__ import annotations


def test_daftar_ditolak_tanpa_login(client):
    """403, bukan 401 — konvensi yang sudah berlaku di seluruh endpoint admin.

    Lihat tests/api/test_kontrak.py: /admin/log dan /admin/pengguna tanpa
    header Authorization juga balas 403.
    """
    response = client.get("/api/v1/admin/indikator")
    assert response.status_code == 403


def test_buat_indikator_berhasil(client, auth):
    response = client.post(
        "/api/v1/admin/indikator",
        data={
            "id_indikator": "ISV-999",
            "kategori": "ISV",
            "nomor": 999,
            "nama_indikator": "Indikator Uji CRUD",
            "sumber_data": "BPS Uji",
            "definisi": "Definisi uji",
        },
        headers=auth,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {"status": "DIBUAT", "id_indikator": "ISV-999"}


def test_buat_indikator_id_tidak_konsisten_ditolak_422(client, auth):
    response = client.post(
        "/api/v1/admin/indikator",
        data={"id_indikator": "ISV-001", "kategori": "ISV", "nomor": 999, "nama_indikator": "X"},
        headers=auth,
    )
    assert response.status_code == 422


def test_buat_indikator_duplikat_ditolak_409(client, auth):
    response = client.post(
        "/api/v1/admin/indikator",
        data={"id_indikator": "ISV-999", "kategori": "ISV", "nomor": 999, "nama_indikator": "Duplikat"},
        headers=auth,
    )
    assert response.status_code == 409


def test_daftar_admin_menyertakan_indikator_baru(client, auth):
    response = client.get("/api/v1/admin/indikator", params={"q": "Indikator Uji CRUD"}, headers=auth)
    assert response.status_code == 200
    baris = response.json()["data"]
    assert any(item["id_indikator"] == "ISV-999" for item in baris)
    satu = next(item for item in baris if item["id_indikator"] == "ISV-999")
    assert satu["punya_nilai"] is False


def test_detail_admin_menyertakan_metadata(client, auth):
    response = client.get("/api/v1/admin/indikator/ISV-999", headers=auth)
    assert response.status_code == 200
    body = response.json()
    assert body["nama_indikator"] == "Indikator Uji CRUD"
    assert body["metadata"]["definisi"] == "Definisi uji"


def test_detail_admin_404_untuk_id_tidak_ada(client, auth):
    response = client.get("/api/v1/admin/indikator/ISV-000", headers=auth)
    assert response.status_code == 404


def test_perbarui_indikator_berhasil_dan_tercatat_di_log(client, auth):
    response = client.put(
        "/api/v1/admin/indikator/ISV-999",
        data={"kategori": "ISV", "nomor": 999, "nama_indikator": "Indikator Uji CRUD (Direvisi)"},
        headers=auth,
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "DIPERBARUI"}

    ulang = client.get("/api/v1/admin/indikator/ISV-999", headers=auth)
    assert ulang.json()["nama_indikator"] == "Indikator Uji CRUD (Direvisi)"

    log = client.get("/api/v1/admin/log", headers=auth)
    assert any(
        baris["id_indikator"] == "ISV-999" and baris["field"] == "nama_indikator" for baris in log.json()["data"]
    )


def test_perbarui_kategori_tidak_konsisten_ditolak_422(client, auth):
    response = client.put(
        "/api/v1/admin/indikator/ISV-999",
        data={"kategori": "IUP", "nomor": 999, "nama_indikator": "X"},
        headers=auth,
    )
    assert response.status_code == 422


def test_hapus_diblokir_saat_indikator_punya_nilai(client, auth):
    # ISV-001 dari _isi_benih() punya banyak baris nilai_indikator.
    response = client.delete("/api/v1/admin/indikator/ISV-001", headers=auth)
    assert response.status_code == 409


def test_hapus_berhasil_saat_tidak_punya_nilai(client, auth):
    response = client.delete("/api/v1/admin/indikator/ISV-999", headers=auth)
    assert response.status_code == 200
    assert response.json() == {"status": "DIHAPUS"}

    ulang = client.get("/api/v1/admin/indikator/ISV-999", headers=auth)
    assert ulang.status_code == 404


def test_hapus_404_untuk_id_tidak_ada(client, auth):
    response = client.delete("/api/v1/admin/indikator/ISV-999", headers=auth)
    assert response.status_code == 404


def test_hapus_diblokir_saat_indikator_punya_usulan(client, auth):
    """usulan_nilai.id_indikator FK NOT NULL tanpa ON DELETE — harus 409, bukan 500.

    ISV-997 dibuat khusus di tes ini dan tidak punya baris nilai_indikator
    sama sekali, jadi yang benar-benar diuji adalah penjaga usulan, bukan
    penjaga nilai yang sudah diuji di tes sebelumnya.
    """
    buat = client.post(
        "/api/v1/admin/indikator",
        data={"id_indikator": "ISV-997", "kategori": "ISV", "nomor": 997, "nama_indikator": "Uji Usulan"},
        headers=auth,
    )
    assert buat.status_code == 200, buat.text

    usulan = client.post(
        "/api/v1/admin/usulan",
        data={
            "id_indikator": "ISV-997",
            "tahun": 2025,
            "jenis": "realisasi",
            "nilai": 1.0,
            "sumber": "Uji",
            "wilayah_kode": "65",
        },
        files={"bukti": ("bukti.pdf", b"%PDF-1.4 uji", "application/pdf")},
        headers=auth,
    )
    assert usulan.status_code == 200, usulan.text

    response = client.delete("/api/v1/admin/indikator/ISV-997", headers=auth)
    assert response.status_code == 409


def test_hapus_tetap_bisa_setelah_indikator_pernah_disunting(client, auth):
    """Menyunting indikator menulis log_perubahan (FK tanpa ON DELETE).

    Tanpa pelepasan jejak itu, indikator yang pernah diedit tidak akan
    pernah bisa dihapus lagi — basis data menolak dengan 500.
    """
    client.post(
        "/api/v1/admin/indikator",
        data={"id_indikator": "ISV-996", "kategori": "ISV", "nomor": 996, "nama_indikator": "Sebelum"},
        headers=auth,
    )
    ubah = client.put(
        "/api/v1/admin/indikator/ISV-996",
        data={"kategori": "ISV", "nomor": 996, "nama_indikator": "Sesudah"},
        headers=auth,
    )
    assert ubah.status_code == 200, ubah.text

    response = client.delete("/api/v1/admin/indikator/ISV-996", headers=auth)
    assert response.status_code == 200, response.text
    assert client.get("/api/v1/admin/indikator/ISV-996", headers=auth).status_code == 404


def test_buat_indikator_menerima_kolom_angka_opsional_kosong(client, auth):
    """Form mengirim "" untuk kolom angka yang dibiarkan kosong, bukan absen.

    Tanpa penanganan itu Pydantic menolak seluruh form dengan 422
    int_parsing — padahal membiarkan "Tahun data terakhir" kosong adalah
    kasus paling lazim saat menambah indikator baru.
    """
    response = client.post(
        "/api/v1/admin/indikator",
        data={
            "id_indikator": "ISV-995",
            "kategori": "ISV",
            "nomor": 995,
            "nama_indikator": "Tanpa Tahun Terakhir",
            "tahun_terakhir": "",
            "satuan": "",
        },
        headers=auth,
    )
    assert response.status_code == 200, response.text
    detail = client.get("/api/v1/admin/indikator/ISV-995", headers=auth).json()
    assert detail["tahun_terakhir"] is None
    assert detail["satuan"] is None

    client.delete("/api/v1/admin/indikator/ISV-995", headers=auth)


def test_perbarui_indikator_menerima_tahun_terakhir_kosong(client, auth):
    client.post(
        "/api/v1/admin/indikator",
        data={
            "id_indikator": "ISV-994",
            "kategori": "ISV",
            "nomor": 994,
            "nama_indikator": "Punya Tahun",
            "tahun_terakhir": 2025,
        },
        headers=auth,
    )
    response = client.put(
        "/api/v1/admin/indikator/ISV-994",
        data={"kategori": "ISV", "nomor": 994, "nama_indikator": "Punya Tahun", "tahun_terakhir": ""},
        headers=auth,
    )
    assert response.status_code == 200, response.text
    assert client.get("/api/v1/admin/indikator/ISV-994", headers=auth).json()["tahun_terakhir"] is None

    client.delete("/api/v1/admin/indikator/ISV-994", headers=auth)
