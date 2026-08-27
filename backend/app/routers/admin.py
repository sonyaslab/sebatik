"""Endpoint administrasi akun dan audit."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Form, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..deps import get_session, id_terautentikasi, wajib_peran
from ..models import Peran
from ..repositories import indikator as repo_indikator
from ..repositories import pengguna as repo_pengguna
from ..repositories import tata_kelola as repo_tata_kelola
from ..repositories.pengguna import ProfilPengguna
from ..schemas.admin import DaftarAkunResponse, LogResponse, PenggunaDibuatResponse
from ..schemas.indikator import (
    DaftarIndikatorAdminResponse,
    IndikatorAdminDetailResponse,
    IndikatorDibuatResponse,
    IndikatorFormBuat,
    IndikatorFormDasar,
    OpsiFormIndikatorResponse,
)
from ..schemas.umum import StatusResponse
from ..services import auth as svc_auth
from ..services import indikator as svc_indikator
from ..services import pengguna as svc

router = APIRouter(prefix="/api/v1", tags=["admin"])

hanya_admin = wajib_peran(Peran.ADMIN)


@router.post("/admin/pengguna", response_model=PenggunaDibuatResponse)
def buat_pengguna(
    username: str = Form(...),
    nama: str = Form(...),
    password: str = Form(...),
    peran: str = Form(...),
    wilayah_kode: str | None = Form(None),
    tim_pjk: str | None = Form(None),
    admin: ProfilPengguna = Depends(hanya_admin),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    penolakan = svc.periksa_pembuatan(
        peran=peran,
        wilayah_aktif=svc.wilayah_penempatan_sah(session, wilayah_kode),
        wilayah_kode=wilayah_kode,
        password=password,
    )
    if penolakan:
        raise HTTPException(penolakan.kode, penolakan.pesan)

    svc.buat(
        session,
        username=username,
        nama=nama,
        password=password,
        peran=peran,
        wilayah_kode=wilayah_kode,
        tim_pjk=tim_pjk,
    )
    try:
        session.commit()
    except IntegrityError as exc:
        # Hanya pelanggaran keunikan yang berarti "username sudah dipakai";
        # galat lain tidak boleh disamarkan menjadi 409.
        session.rollback()
        raise HTTPException(409, "Username sudah digunakan") from exc
    svc_auth.catat_peristiwa(
        "akun_dibuat", pengguna_id=id_terautentikasi(admin), username=username, hasil="berhasil", peran_baru=peran
    )
    return {"status": "DIBUAT", "username": username}


@router.get("/admin/pengguna", response_model=DaftarAkunResponse)
def daftar_pengguna(
    admin: ProfilPengguna = Depends(hanya_admin),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return svc.daftar(session)


@router.patch("/admin/pengguna/{pengguna_id}/status", response_model=StatusResponse)
def ubah_status_pengguna(
    pengguna_id: int,
    aktif: bool = Form(...),
    admin: ProfilPengguna = Depends(hanya_admin),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    penolakan = svc.periksa_ubah_status(pengguna_id=pengguna_id, admin_id=admin.id, aktif=aktif)
    if penolakan:
        raise HTTPException(penolakan.kode, penolakan.pesan)
    akun = repo_pengguna.ambil(session, pengguna_id)
    if akun is None:
        raise HTTPException(404, "Pengguna tidak ditemukan")
    return svc.ubah_status(session, akun, aktif=aktif, admin_id=id_terautentikasi(admin))


@router.post("/admin/pengguna/{pengguna_id}/reset-password", response_model=StatusResponse)
def reset_password(
    pengguna_id: int,
    password_baru: str = Form(...),
    admin: ProfilPengguna = Depends(hanya_admin),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    if not svc_auth.password_layak(password_baru):
        raise HTTPException(422, svc.PESAN_PASSWORD_PENDEK)
    akun = repo_pengguna.ambil(session, pengguna_id)
    if akun is None:
        raise HTTPException(404, "Pengguna tidak ditemukan")

    hasil = svc.reset_password(session, akun, password_baru=password_baru, admin_id=id_terautentikasi(admin))
    svc_auth.catat_peristiwa(
        "reset_password", pengguna_id=id_terautentikasi(admin), hasil="berhasil", target_id=pengguna_id
    )
    return hasil


@router.get("/admin/log", response_model=LogResponse)
def log_audit(
    admin: ProfilPengguna = Depends(hanya_admin),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return {"data": repo_tata_kelola.daftar_log_perubahan(session)}


# --- CRUD indikator ---------------------------------------------------------
#
# Form dikirim sebagai multipart/form-data seperti endpoint mutasi lain di
# berkas ini, tetapi field-nya ~30 buah — jadi dipakai satu parameter
# Annotated[Model, Form()] alih-alih 30 parameter Form() skalar. Bentuk di
# kabel tidak berubah, hanya tanda tangan fungsinya yang dikelompokkan.


@router.get("/admin/indikator", response_model=DaftarIndikatorAdminResponse)
def daftar_indikator_admin(
    q: str | None = None,
    kategori: list[str] | None = Query(None),
    kelompok: list[str] | None = Query(None),
    tim: list[str] | None = Query(None),
    sort: str = "id_indikator",
    order: Literal["asc", "desc"] = "asc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    admin: ProfilPengguna = Depends(hanya_admin),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return svc_indikator.daftar_admin(
        session,
        q=q,
        kategori=kategori,
        kelompok=kelompok,
        tim=tim,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )


@router.get("/admin/indikator-opsi", response_model=OpsiFormIndikatorResponse)
def opsi_form_indikator_admin(
    admin: ProfilPengguna = Depends(hanya_admin),
    session: Session = Depends(get_session),
) -> dict[str, list[str]]:
    return svc_indikator.opsi_form_admin(session)


@router.get("/admin/indikator/{id_indikator}", response_model=IndikatorAdminDetailResponse)
def detail_indikator_admin(
    id_indikator: str,
    admin: ProfilPengguna = Depends(hanya_admin),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    indikator = repo_indikator.ambil(session, id_indikator)
    if indikator is None:
        raise HTTPException(404, "Indikator tidak ditemukan")
    return svc_indikator.detail_admin(session, indikator)


@router.post("/admin/indikator", response_model=IndikatorDibuatResponse)
def buat_indikator_admin(
    form: Annotated[IndikatorFormBuat, Form()],
    admin: ProfilPengguna = Depends(hanya_admin),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    penolakan = svc_indikator.periksa_konsistensi_id(form.id_indikator, form.kategori, form.nomor)
    if penolakan:
        raise HTTPException(penolakan.kode, penolakan.pesan)
    penolakan = svc_indikator.periksa_pilihan_klasifikasi(
        session, kelompok=form.kelompok, kelompok_makro=form.kelompok_makro
    )
    if penolakan:
        raise HTTPException(penolakan.kode, penolakan.pesan)
    try:
        indikator = svc_indikator.buat_indikator(session, form, pengguna_id=id_terautentikasi(admin))
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "id_indikator sudah dipakai") from exc
    return {"status": "DIBUAT", "id_indikator": indikator.id_indikator}


@router.put("/admin/indikator/{id_indikator}", response_model=StatusResponse)
def perbarui_indikator_admin(
    id_indikator: str,
    form: Annotated[IndikatorFormDasar, Form()],
    admin: ProfilPengguna = Depends(hanya_admin),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    indikator = repo_indikator.ambil(session, id_indikator)
    if indikator is None:
        raise HTTPException(404, "Indikator tidak ditemukan")
    penolakan = svc_indikator.periksa_konsistensi_id(id_indikator, form.kategori, form.nomor)
    if penolakan:
        raise HTTPException(penolakan.kode, penolakan.pesan)
    penolakan = svc_indikator.periksa_pilihan_klasifikasi(
        session, kelompok=form.kelompok, kelompok_makro=form.kelompok_makro
    )
    if penolakan:
        raise HTTPException(penolakan.kode, penolakan.pesan)
    metadata = repo_indikator.ambil_metadata(session, id_indikator)
    return svc_indikator.perbarui_indikator(session, indikator, metadata, form, pengguna_id=id_terautentikasi(admin))


@router.delete("/admin/indikator/{id_indikator}", response_model=StatusResponse)
def hapus_indikator_admin(
    id_indikator: str,
    konfirmasi: str = Query(""),
    admin: ProfilPengguna = Depends(hanya_admin),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    penolakan = svc_indikator.periksa_konfirmasi_penghapusan(id_indikator, konfirmasi)
    if penolakan:
        raise HTTPException(penolakan.kode, penolakan.pesan)
    indikator = repo_indikator.ambil(session, id_indikator)
    if indikator is None:
        raise HTTPException(404, "Indikator tidak ditemukan")
    return svc_indikator.hapus_indikator(session, indikator, pengguna_id=id_terautentikasi(admin))
