/* @vitest-environment jsdom */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import {createRoot} from 'react-dom/client'
import {act} from 'react'
import {MemoryRouter} from 'react-router-dom'

import AdminPage from './AdminPage'
import * as endpoints from '../api/endpoints'
import {clearToken, setToken} from '../auth'
import {AuthProvider} from '../context/AuthContext'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

let root
let wadah

async function render(element) {
  wadah = document.createElement('div')
  document.body.appendChild(wadah)
  root = createRoot(wadah)
  await act(async () =>
    root.render(
      <MemoryRouter>
        <AuthProvider>{element}</AuthProvider>
      </MemoryRouter>,
    ),
  )
  return wadah
}

beforeEach(() => {
  setToken('token-uji')
})

afterEach(() => {
  if (root) act(() => root.unmount())
  wadah?.remove()
  root = undefined
  clearToken()
  vi.restoreAllMocks()
})

/* Akun yang masih menyandang bendera ditolak 403 di seluruh rute istimewa.
   Ruang kerja tidak boleh dirender — bukan hanya karena tampilannya kosong,
   tetapi karena panel di dalamnya memuat datanya sendiri saat dipasang. */
describe('gerbang wajib ganti sandi', () => {
  it('menampilkan layar ganti sandi dan tidak memuat antrean usulan', async () => {
    vi.spyOn(endpoints, 'profilSaya').mockResolvedValue({
      peran: 'OPERATOR',
      nama: 'Operator Baru',
      harus_ganti_password: true,
    })
    const antrean = vi.spyOn(endpoints, 'daftarUsulan').mockResolvedValue({data: []})
    const wilayah = vi.spyOn(endpoints, 'wilayah').mockResolvedValue({data: []})

    const el = await render(<AdminPage />)

    expect(el.textContent).toContain('Ganti kata sandi dulu')
    expect(el.querySelector('[name="password_lama"]')).toBeTruthy()
    expect(el.querySelector('[name="password_baru"]')).toBeTruthy()
    expect(antrean).not.toHaveBeenCalled()
    expect(wilayah).not.toHaveBeenCalled()
  })

  it('membuka ruang kerja setelah bendera padam', async () => {
    vi.spyOn(endpoints, 'profilSaya').mockResolvedValue({
      peran: 'OPERATOR',
      nama: 'Operator Lama',
      harus_ganti_password: false,
    })
    const antrean = vi.spyOn(endpoints, 'daftarUsulan').mockResolvedValue({data: []})
    vi.spyOn(endpoints, 'wilayah').mockResolvedValue({data: []})
    vi.spyOn(endpoints, 'capaianExplorer').mockResolvedValue({indikator: []})

    const el = await render(<AdminPage />)

    expect(el.textContent).not.toContain('Ganti kata sandi dulu')
    expect(antrean).toHaveBeenCalled()
  })
})
