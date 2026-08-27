/* @vitest-environment jsdom */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import {createRoot} from 'react-dom/client'
import {act} from 'react'

import {IndikatorManager, pesanGalat} from './IndikatorManager'
import * as endpoints from '../../api/endpoints'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

let root
let wadah

const opsi = {
  kelompok: ['Transformasi Sosial'],
  kelompok_makro: ['Non-Makro'],
}

beforeEach(() => {
  vi.spyOn(endpoints, 'opsiFormIndikatorAdmin').mockResolvedValue(opsi)
})

function render(element) {
  wadah = document.createElement('div')
  document.body.appendChild(wadah)
  root = createRoot(wadah)
  act(() => root.render(element))
  return wadah
}

afterEach(() => {
  if (root) act(() => root.unmount())
  wadah?.remove()
  root = undefined
  vi.restoreAllMocks()
})

const baris = {
  id_indikator: 'ISV-999',
  kategori: 'ISV',
  nomor: 999,
  nama_indikator: 'Indikator Uji',
  kelompok: 'Kelompok Uji',
  status_ketersediaan: 'Tersedia',
  punya_nilai: false,
}

describe('IndikatorManager', () => {
  it('menampilkan baris dari daftarIndikatorAdmin', async () => {
    vi.spyOn(endpoints, 'daftarIndikatorAdmin').mockResolvedValue({data: [baris], total: 1, page: 1, page_size: 25})
    render(<IndikatorManager />)
    await act(async () => {})
    expect(wadah.textContent).toContain('Indikator Uji')
  })

  it('tetap mengaktifkan tombol hapus saat indikator punya nilai', async () => {
    vi.spyOn(endpoints, 'daftarIndikatorAdmin').mockResolvedValue({
      data: [{...baris, punya_nilai: true}],
      total: 1,
      page: 1,
      page_size: 25,
    })
    render(<IndikatorManager />)
    await act(async () => {})
    const tombolHapus = wadah.querySelector('[data-uji="hapus-ISV-999"]')
    expect(tombolHapus.disabled).toBe(false)
  })

  it('memanggil buatIndikatorAdmin saat form tambah disubmit', async () => {
    vi.spyOn(endpoints, 'daftarIndikatorAdmin').mockResolvedValue({data: [], total: 0, page: 1, page_size: 25})
    const buat = vi
      .spyOn(endpoints, 'buatIndikatorAdmin')
      .mockResolvedValue({status: 'DIBUAT', id_indikator: 'ISV-999'})
    render(<IndikatorManager />)
    await act(async () => {})

    await act(async () => wadah.querySelector('[data-uji="tombol-tambah"]').click())

    const form = wadah.querySelector('[data-uji="form-indikator"]')
    form.querySelector('[name="id_indikator"]').value = 'ISV-999'
    form.querySelector('[name="kategori"]').value = 'ISV'
    form.querySelector('[name="nomor"]').value = '999'
    form.querySelector('[name="nama_indikator"]').value = 'Indikator Uji'
    form.querySelector('[name="kelompok"]').value = 'Transformasi Sosial'
    form.querySelector('[name="kelompok_makro"]').value = 'Non-Makro'

    await act(async () => form.requestSubmit())

    expect(buat).toHaveBeenCalledTimes(1)
    expect(buat.mock.calls[0][0].get('id_indikator')).toBe('ISV-999')
  })

  it('memanggil hapusIndikatorAdmin saat tombol hapus ditekan dan dikonfirmasi', async () => {
    vi.spyOn(endpoints, 'daftarIndikatorAdmin').mockResolvedValue({data: [baris], total: 1, page: 1, page_size: 25})
    const hapus = vi.spyOn(endpoints, 'hapusIndikatorAdmin').mockResolvedValue({status: 'DIHAPUS'})
    render(<IndikatorManager />)
    await act(async () => {})

    await act(async () => wadah.querySelector('[data-uji="hapus-ISV-999"]').click())
    expect(wadah.textContent).toContain('Apakah Anda yakin ingin menghapus?')
    await act(async () => wadah.querySelector('.indicator-confirm-delete').click())

    expect(hapus).toHaveBeenCalledWith('ISV-999', 'ISV-999')
  })

  it('mengambil detail lengkap sebelum membuka form edit', async () => {
    vi.spyOn(endpoints, 'daftarIndikatorAdmin').mockResolvedValue({data: [baris], total: 1, page: 1, page_size: 25})
    const detail = vi
      .spyOn(endpoints, 'detailIndikatorAdmin')
      .mockResolvedValue({...baris, metadata: {definisi: 'Definisi tersimpan'}})
    render(<IndikatorManager />)
    await act(async () => {})

    await act(async () => wadah.querySelector('[data-uji="edit-ISV-999"]').click())

    expect(detail).toHaveBeenCalledWith('ISV-999')
    const form = wadah.querySelector('[data-uji="form-indikator"]')
    expect(form.querySelector('[name="definisi"]').value).toBe('Definisi tersimpan')
    // kategori/nomor jadi input hidden saat edit supaya tetap ikut terkirim.
    expect(form.querySelector('[name="kategori"]').type).toBe('hidden')
  })
})

describe('pesanGalat', () => {
  it('meratakan detail 422 FastAPI (daftar objek) jadi satu kalimat', () => {
    const galat = {
      detail: [
        {loc: ['body', 'tahun_terakhir'], msg: 'Input should be a valid integer', type: 'int_parsing'},
        {loc: ['body', 'nomor'], msg: 'Field required', type: 'missing'},
      ],
    }
    expect(pesanGalat(galat, 'cadangan')).toBe('Input should be a valid integer; Field required')
  })

  it('meneruskan detail berupa teks apa adanya', () => {
    expect(pesanGalat({detail: 'Kategori harus ISV atau IUP'}, 'cadangan')).toBe('Kategori harus ISV atau IUP')
  })

  it('jatuh ke pesan cadangan bila galat tidak punya bentuk yang dikenal', () => {
    expect(pesanGalat({}, 'cadangan')).toBe('cadangan')
    expect(pesanGalat(undefined, 'cadangan')).toBe('cadangan')
  })
})

describe('IndikatorManager galat', () => {
  it('menampilkan galat 422 sebagai teks, bukan merender objek', async () => {
    vi.spyOn(endpoints, 'daftarIndikatorAdmin').mockRejectedValue({
      detail: [{loc: ['body', 'tahun_terakhir'], msg: 'Input should be a valid integer'}],
    })
    render(<IndikatorManager />)
    await act(async () => {})
    expect(wadah.textContent).toContain('Input should be a valid integer')
  })
})
