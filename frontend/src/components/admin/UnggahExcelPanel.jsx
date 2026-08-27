import {useEffect, useRef, useState} from 'react'
import {FileSpreadsheet, ShieldCheck, Upload} from 'lucide-react'
import {EmptyState, Panel} from '../../ui'
import {pratinjauUnggahan, riwayatUnggahan, setujuiUnggahan} from '../../api/endpoints'
import {dateText} from '../../lib/format'

/* Diff penuh bisa ratusan baris; merender semuanya membuat halaman admin
   tersendat tanpa menambah informasi yang berguna. */
const BATAS_BARIS = 200

/* Galat 422 FastAPI berupa DAFTAR objek, bukan kalimat. Merendernya apa adanya
   melempar "Objects are not valid as a React child". */
export function pesanGalatUnggah(error, cadangan) {
  const detail = error?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail)) {
    const teks = detail
      .map(item => (typeof item === 'string' ? item : item?.msg))
      .filter(Boolean)
      .join('; ')
    if (teks) return teks
  }
  return error?.message || cadangan
}

const angka = nilai => (nilai === null || nilai === undefined ? '—' : nilai)

/* Log butuh jam, bukan sekadar tanggal: satu berkas bisa diunggah dan
   diterapkan pada hari yang sama. */
function waktuTeks(nilai) {
  if (!nilai) return '—'
  const waktu = new Date(nilai)
  if (Number.isNaN(waktu.getTime())) return dateText(nilai)
  return `${dateText(nilai)} ${waktu.toLocaleTimeString('id-ID', {hour: '2-digit', minute: '2-digit'})}`
}

function TabelNilai({baris, konflik = false, uji}) {
  const tampil = baris.slice(0, BATAS_BARIS)
  return (
    <div className="table-scroll" data-uji={uji}>
      <table className="workspace-table">
        <thead>
          <tr>
            <th>Indikator</th>
            <th>Tahun</th>
            <th>Jenis</th>
            <th>Lama</th>
            <th>Baru</th>
            {konflik && <th>Sumber</th>}
          </tr>
        </thead>
        <tbody>
          {tampil.map(item => (
            <tr key={`${item.id}-${item.tahun}-${item.jenis}`}>
              <td>
                <b>{item.id}</b>
              </td>
              <td>{item.tahun}</td>
              <td>{item.jenis}</td>
              <td>{angka(item.lama)}</td>
              <td>{angka(item.baru)}</td>
              {konflik && (
                <td>
                  <span className="indicator-state proxy">hasil verifikasi #{item.usulan_id}</span>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      {baris.length > tampil.length && (
        <p className="form-hint">… dan {baris.length - tampil.length} baris lainnya</p>
      )}
    </div>
  )
}

export function UnggahExcelPanel({onNotify, onSelesai}) {
  const [pratinjau, setPratinjau] = useState(null)
  const [sibuk, setSibuk] = useState(false)
  const [riwayat, setRiwayat] = useState([])
  /* Pesan juga ditahan di dalam panel. `onNotify` merender notice di puncak
     halaman admin yang panjang — kalau unggahan gagal, admin yang sedang
     melihat panel ini tidak melihat apa pun dan mengira tombolnya mati. */
  const [kabar, setKabar] = useState(null)
  const inputRef = useRef(null)

  /* Satu pintu pesan: tampil di dalam panel DAN di notice halaman. */
  const lapor = (teks, nada) => {
    setKabar({teks, nada})
    onNotify?.(teks, nada === 'success' ? 'success' : 'warning')
  }

  const muatRiwayat = async () => {
    try {
      const hasil = await riwayatUnggahan()
      setRiwayat(hasil.data || [])
    } catch {
      /* Riwayat hanya pelengkap; kegagalannya tidak boleh menutup panel. */
    }
  }

  useEffect(() => {
    muatRiwayat()
  }, [])

  const kirimPratinjau = async event => {
    event.preventDefault()
    const berkas = inputRef.current?.files?.[0]
    if (!berkas) {
      lapor('Pilih berkas .xlsx lebih dulu.', 'warning')
      return
    }
    const form = new FormData()
    form.set('file', berkas)
    setSibuk(true)
    setKabar(null)
    try {
      const hasil = await pratinjauUnggahan(form)
      setPratinjau(hasil)
    } catch (error) {
      lapor(pesanGalatUnggah(error, 'Pratinjau unggahan gagal'), 'warning')
    } finally {
      setSibuk(false)
    }
  }

  const setujui = async () => {
    if (!confirm('Muat dataset ini ke basis data? Nilai indikator akan diperbarui.')) return
    setSibuk(true)
    try {
      await setujuiUnggahan(pratinjau.id)
      lapor('Dataset berhasil dimuat.', 'success')
      setPratinjau(null)
      if (inputRef.current) inputRef.current.value = ''
      muatRiwayat()
      onSelesai?.()
    } catch (error) {
      lapor(pesanGalatUnggah(error, 'Persetujuan unggahan gagal'), 'warning')
    } finally {
      setSibuk(false)
    }
  }

  const batal = () => {
    setPratinjau(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  const diff = pratinjau?.diff
  const ringkasan = diff?.ringkasan

  return (
    <Panel
      delay={40}
      kicker="Unggah massal"
      title="Unggah Excel indikator"
      desc="Unggah berkas .xlsx basis data indikator, periksa pratinjau, lalu setujui untuk memuatnya."
    >
      {kabar && (
        <p className={`unggah-kabar ${kabar.nada}`} data-uji="kabar" role="status">
          {kabar.teks}
        </p>
      )}

      {!pratinjau && (
        <form className="unggah-form" data-uji="form-unggah" onSubmit={kirimPratinjau}>
          <label className="unggah-berkas">
            <span>Berkas Excel (.xlsx)</span>
            <input ref={inputRef} data-uji="input-berkas" type="file" name="file" accept=".xlsx" required />
          </label>
          <button className="unggah-tombol" data-uji="tombol-pratinjau" disabled={sibuk}>
            <Upload size={16} aria-hidden="true" />
            {sibuk ? 'Memproses…' : 'Pratinjau'}
          </button>
          <small className="unggah-petunjuk">
            Wajib memuat sheet <b>Basis Data Indikator</b> (86 baris) dan <b>Data Target-Realisasi</b>.
            Sheet nilai boleh terisi sebagian.
          </small>
        </form>
      )}

      {diff && (
        <div className="unggah-diff" data-uji="pratinjau">
          <div className="role-counts" data-uji="ringkasan">
            <div>
              <b>{diff.indikator_baru.length}</b>
              <span>INDIKATOR BARU</span>
            </div>
            <div>
              <b>{diff.indikator_hilang.length}</b>
              <span>TIDAK ADA DI BERKAS</span>
            </div>
            <div>
              <b>{diff.nilai_berubah.length}</b>
              <span>NILAI BERUBAH</span>
            </div>
            <div>
              <b>{ringkasan?.nilai_dilindungi ?? 0}</b>
              <span>NILAI DILINDUNGI</span>
            </div>
          </div>

          {diff.nilai_berubah.length > 0 && (
            <>
              <h4>Nilai yang akan dimuat</h4>
              <TabelNilai baris={diff.nilai_berubah} uji="tabel-berubah" />
            </>
          )}

          {diff.nilai_konflik.length > 0 && (
            <>
              <h4>
                <ShieldCheck size={16} /> Nilai dilindungi
              </h4>
              <p className="form-hint">
                Baris berikut berasal dari alur verifikasi operator dan <b>tidak</b> akan ditimpa unggahan ini.
              </p>
              <div className="unggah-konflik">
                <TabelNilai baris={diff.nilai_konflik} konflik uji="tabel-konflik" />
              </div>
            </>
          )}

          <div className="row-actions">
            <button type="button" onClick={batal} disabled={sibuk}>
              Batal
            </button>
            <button type="button" data-uji="tombol-setujui" onClick={setujui} disabled={sibuk}>
              {sibuk ? 'Memuat…' : 'Setujui & muat'}
            </button>
          </div>
        </div>
      )}

      <h4 className="unggah-riwayat">Riwayat unggahan</h4>
      {riwayat.length ? (
        <div className="table-scroll">
          <table className="workspace-table">
            <thead>
              <tr>
                <th>Berkas</th>
                <th>Diunggah</th>
                <th>Perubahan diterapkan</th>
                <th>Hasil</th>
                <th>Oleh</th>
              </tr>
            </thead>
            <tbody>
              {riwayat.map(item => (
                <tr key={item.id}>
                  <td>
                    <FileSpreadsheet size={14} /> {item.nama_file_asli}
                  </td>
                  <td>{waktuTeks(item.diunggah_pada)}</td>
                  <td>
                    {item.diterapkan_pada ? (
                      waktuTeks(item.diterapkan_pada)
                    ) : (
                      <span className="unggah-belum">belum diterapkan</span>
                    )}
                  </td>
                  <td>
                    {item.diterapkan_pada ? (
                      <>
                        {item.nilai_dimuat ?? 0} nilai dimuat
                        {item.nilai_dilindungi ? `, ${item.nilai_dilindungi} dilindungi` : ''}
                      </>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>{item.oleh || 'sistem'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState compact title="Belum ada unggahan" desc="Riwayat unggahan Excel akan tampil di sini." />
      )}
    </Panel>
  )
}
