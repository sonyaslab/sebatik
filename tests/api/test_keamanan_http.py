"""Tes keamanan pada tingkat HTTP: header, pembatas laju, dan kebocoran data."""

from __future__ import annotations

from .conftest import SANDI_ADMIN

# Pembersihan pembatas laju antar-tes ditangani fixture autouse di conftest.py,
# supaya seluruh modul tes API mendapat isolasi yang sama.


def test_header_keamanan_terpasang_di_semua_respons(client):
    response = client.get("/api/v1/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_hsts_tidak_dipasang_pada_http(client):
    """HSTS di atas HTTP diabaikan peramban dan mengunci pengembangan lokal."""
    assert "Strict-Transport-Security" not in client.get("/api/v1/health").headers


def test_percobaan_masuk_dibatasi(client):
    salah = {"username": "admin", "password": "sandi-salah-sekali"}
    kode = [client.post("/api/v1/auth/login", data=salah).status_code for _ in range(6)]
    assert kode[:5] == [401] * 5
    assert kode[5] == 429


def test_respons_429_memberi_tahu_kapan_boleh_mencoba_lagi(client):
    salah = {"username": "operator.6501.1", "password": "sandi-salah-sekali"}
    for _ in range(5):
        client.post("/api/v1/auth/login", data=salah)
    response = client.post("/api/v1/auth/login", data=salah)
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


def test_masuk_berhasil_mengosongkan_jatah(client):
    """Pengguna sah tidak boleh terkunci gara-gara salah ketik beberapa kali."""
    for _ in range(4):
        client.post("/api/v1/auth/login", data={"username": "admin", "password": "salah-sekali-lah"})
    benar = {"username": "admin", "password": SANDI_ADMIN}
    assert client.post("/api/v1/auth/login", data=benar).status_code == 200
    # Jatah kembali penuh setelah berhasil.
    assert client.post("/api/v1/auth/login", data=benar).status_code == 200


def test_pembatas_terpisah_antar_username(client):
    for _ in range(6):
        client.post("/api/v1/auth/login", data={"username": "korban", "password": "xxxxxxxxxxxx"})
    lain = client.post("/api/v1/auth/login", data={"username": "admin", "password": "sandi-salah-lain"})
    assert lain.status_code == 401


def test_respons_tidak_membocorkan_hash_kata_sandi(client, auth):
    for path in ("/api/v1/auth/saya", "/api/v1/admin/pengguna"):
        isi = client.get(path, headers=auth).text
        assert "password_hash" not in isi
        assert "$argon2" not in isi


def test_pesan_galat_masuk_tidak_membedakan_username_dan_sandi(client):
    tidak_ada = client.post("/api/v1/auth/login", data={"username": "hantu", "password": "apa-saja-lah-ini"})
    salah_sandi = client.post("/api/v1/auth/login", data={"username": "admin", "password": "salah-sekali-lah"})
    assert tidak_ada.status_code == salah_sandi.status_code == 401
    assert tidak_ada.json()["detail"] == salah_sandi.json()["detail"]


def test_endpoint_admin_menolak_tanpa_token(client):
    for path in ("/api/v1/admin/pengguna", "/api/v1/admin/log"):
        assert client.get(path).status_code == 403


def test_bukti_dukung_tidak_dapat_diakses_tanpa_peran(client):
    assert client.get("/api/v1/admin/usulan/1/bukti").status_code == 403


# --- gerbang wajib ganti sandi awal ----------------------------------------

SANDI_AWAL_WAJIB = "Sandi-Awal-Wajib-2026!"
SANDI_BARU_WAJIB = "Sandi-Baru-Wajib-2026!"


def _akun_berbendera(client, auth) -> dict[str, str]:
    """Akun baru buatan admin selalu `harus_ganti_password=True`."""
    dibuat = client.post(
        "/api/v1/admin/pengguna",
        headers=auth,
        data={
            "username": "operator.wajib.1",
            "nama": "Operator Wajib Ganti",
            "password": SANDI_AWAL_WAJIB,
            "peran": "OPERATOR",
            "wilayah_kode": "6501",
        },
    )
    assert dibuat.status_code == 200, dibuat.text

    masuk = client.post(
        "/api/v1/auth/login",
        data={"username": "operator.wajib.1", "password": SANDI_AWAL_WAJIB},
    )
    assert masuk.status_code == 200
    assert masuk.json()["harus_ganti_password"] is True
    return {"Authorization": f"Bearer {masuk.json()['access_token']}"}


def test_akun_berbendera_diblokir_sampai_sandi_diganti(client, auth):
    """403, bukan 401: tokennya sah, yang belum beres adalah kewajiban ganti sandi."""
    berbendera = _akun_berbendera(client, auth)
    assert client.get("/api/v1/admin/usulan", headers=berbendera).status_code == 403

    tanpa_sandi_lama = client.post(
        "/api/v1/auth/ganti-password",
        headers=berbendera,
        data={"password_baru": SANDI_BARU_WAJIB},
    )
    assert tanpa_sandi_lama.status_code == 422

    sandi_lama_salah = client.post(
        "/api/v1/auth/ganti-password",
        headers=berbendera,
        data={"password_lama": "Sandi-Lama-Salah-2026!", "password_baru": SANDI_BARU_WAJIB},
    )
    assert sandi_lama_salah.status_code == 401
    assert "saat ini" in sandi_lama_salah.json()["detail"].lower()

    berhasil = client.post(
        "/api/v1/auth/ganti-password",
        headers=berbendera,
        data={"password_lama": SANDI_AWAL_WAJIB, "password_baru": SANDI_BARU_WAJIB},
    )
    assert berhasil.status_code == 200
    assert client.get("/api/v1/admin/usulan", headers=berbendera).status_code == 200


def test_sandi_terlalu_panjang_tidak_meledakkan_login(client):
    """Batas panjang dicek sebelum Argon2; jawabannya tetap 401 yang sama."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "a" * 200},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Username atau kata sandi salah"
