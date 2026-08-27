/* @vitest-environment jsdom */
import {afterEach, describe, expect, it, vi} from 'vitest'
import {createRoot} from 'react-dom/client'
import {act} from 'react'

import {UnggahExcelPanel, pesanGalatUnggah} from './UnggahExcelPanel'
import * as endpoints from '../../api/endpoints'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

let root
let wadah

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

const DIFF = {
  indikator_baru: ['ISV-003'],
  indikator_hilang: [],
  nilai_berubah: [{id: 'ISV-003', tahun: 2024, jenis: 'realisasi', lama: null, baru: 42}],
  nilai_konflik: [{id: 'ISV-001', tahun: 2023, jenis: 'realisasi', lama: 777, baru: 1, usulan_id: 9}],
  ringkasan: {indikator: 86, nilai_dimuat: 1, nilai_dilindungi: 1},
}

/* `requestSubmit()` menjalankan constraint validation, dan input file yang
   `required` dianggap kosong oleh jsdom meski `files` sudah dipalsukan — jadi
   event submit dikirim langsung. */
function kirimForm(form) {
  form.dispatchEvent(new Event('submit', {bubbles: true, cancelable: true}))
}

function pasangBerkas(input) {
  const berkas = new File(['xx'], 'basis.xlsx', {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  Object.defineProperty(input, 'files', {value: [berkas], configurable: true})
  return berkas
}

describe('UnggahExcelPanel', () => {
  it('menampilkan riwayat unggahan saat dimuat', async () => {
    vi.spyOn(endpoints, 'riwayatUnggahan').mockResolvedValue({
      data: [{id: 1, nama_file_asli: 'basis.xlsx', status: 'DISETUJUI', dibuat_pada: null, oleh: 'admin'}],
    })
    render(<UnggahExcelPanel onNotify={() => {}} />)
    await act(async () => {})
    expect(wadah.textContent).toContain('basis.xlsx')
    expect(wadah.textContent).toContain('DISETUJUI')
  })

  it('mengirim berkas ke pratinjauUnggahan dan menampilkan tabel konflik', async () => {
    vi.spyOn(endpoints, 'riwayatUnggahan').mockResolvedValue({data: []})
    const pratinjau = vi.spyOn(endpoints, 'pratinjauUnggahan').mockResolvedValue({id: 7, diff: DIFF})
    render(<UnggahExcelPanel onNotify={() => {}} />)
    await act(async () => {})

    pasangBerkas(wadah.querySelector('[data-uji="input-berkas"]'))
    await act(async () => kirimForm(wadah.querySelector('[data-uji="form-unggah"]')))

    expect(pratinjau).toHaveBeenCalledTimes(1)
    expect(pratinjau.mock.calls[0][0].get('file').name).toBe('basis.xlsx')
    expect(wadah.querySelector('[data-uji="tabel-konflik"]')).toBeTruthy()
    expect(wadah.textContent).toContain('hasil verifikasi #9')
    expect(wadah.textContent).toContain('NILAI DILINDUNGI')
  })

  it('menyembunyikan tabel konflik saat tidak ada konflik', async () => {
    vi.spyOn(endpoints, 'riwayatUnggahan').mockResolvedValue({data: []})
    vi.spyOn(endpoints, 'pratinjauUnggahan').mockResolvedValue({
      id: 7,
      diff: {...DIFF, nilai_konflik: [], ringkasan: {...DIFF.ringkasan, nilai_dilindungi: 0}},
    })
    render(<UnggahExcelPanel onNotify={() => {}} />)
    await act(async () => {})

    pasangBerkas(wadah.querySelector('[data-uji="input-berkas"]'))
    await act(async () => kirimForm(wadah.querySelector('[data-uji="form-unggah"]')))

    expect(wadah.querySelector('[data-uji="tabel-konflik"]')).toBeNull()
    expect(wadah.querySelector('[data-uji="tabel-berubah"]')).toBeTruthy()
  })

  it('memanggil setujuiUnggahan dengan id pratinjau setelah dikonfirmasi', async () => {
    vi.spyOn(endpoints, 'riwayatUnggahan').mockResolvedValue({data: []})
    vi.spyOn(endpoints, 'pratinjauUnggahan').mockResolvedValue({id: 7, diff: DIFF})
    const setujui = vi.spyOn(endpoints, 'setujuiUnggahan').mockResolvedValue({status: 'DISETUJUI'})
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const selesai = vi.fn()
    render(<UnggahExcelPanel onNotify={() => {}} onSelesai={selesai} />)
    await act(async () => {})

    pasangBerkas(wadah.querySelector('[data-uji="input-berkas"]'))
    await act(async () => kirimForm(wadah.querySelector('[data-uji="form-unggah"]')))
    await act(async () => wadah.querySelector('[data-uji="tombol-setujui"]').click())

    expect(setujui).toHaveBeenCalledWith(7)
    expect(selesai).toHaveBeenCalled()
  })

  it('tidak memanggil setujuiUnggahan bila konfirmasi dibatalkan', async () => {
    vi.spyOn(endpoints, 'riwayatUnggahan').mockResolvedValue({data: []})
    vi.spyOn(endpoints, 'pratinjauUnggahan').mockResolvedValue({id: 7, diff: DIFF})
    const setujui = vi.spyOn(endpoints, 'setujuiUnggahan').mockResolvedValue({status: 'DISETUJUI'})
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    render(<UnggahExcelPanel onNotify={() => {}} />)
    await act(async () => {})

    pasangBerkas(wadah.querySelector('[data-uji="input-berkas"]'))
    await act(async () => kirimForm(wadah.querySelector('[data-uji="form-unggah"]')))
    await act(async () => wadah.querySelector('[data-uji="tombol-setujui"]').click())

    expect(setujui).not.toHaveBeenCalled()
  })

  it('melaporkan galat 422 sebagai teks lewat onNotify', async () => {
    vi.spyOn(endpoints, 'riwayatUnggahan').mockResolvedValue({data: []})
    vi.spyOn(endpoints, 'pratinjauUnggahan').mockRejectedValue({detail: 'Master harus berisi tepat 86 ID unik'})
    const notify = vi.fn()
    render(<UnggahExcelPanel onNotify={notify} />)
    await act(async () => {})

    pasangBerkas(wadah.querySelector('[data-uji="input-berkas"]'))
    await act(async () => kirimForm(wadah.querySelector('[data-uji="form-unggah"]')))

    expect(notify).toHaveBeenCalledWith('Master harus berisi tepat 86 ID unik')
  })
})

describe('pesanGalatUnggah', () => {
  it('meratakan daftar galat 422 jadi satu kalimat', () => {
    const galat = {detail: [{msg: 'Field required'}, {msg: 'Input should be a valid integer'}]}
    expect(pesanGalatUnggah(galat, 'cadangan')).toBe('Field required; Input should be a valid integer')
  })

  it('jatuh ke cadangan bila bentuk galat tidak dikenal', () => {
    expect(pesanGalatUnggah({}, 'cadangan')).toBe('cadangan')
  })
})
