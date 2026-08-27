import {useEffect, useState} from 'react'
import {Pencil, Plus, Trash2} from 'lucide-react'
import {EmptyState, Panel} from '../../ui'
import {
  buatIndikatorAdmin,
  daftarIndikatorAdmin,
  detailIndikatorAdmin,
  hapusIndikatorAdmin,
  perbaruiIndikatorAdmin,
} from '../../api/endpoints'

/* FastAPI membalas 422 dengan `detail` berupa DAFTAR objek galat
   ({loc, msg, type}), bukan kalimat. Merendernya apa adanya membuat React
   melempar "Objects are not valid as a React child" dan seluruh halaman
   admin berubah jadi layar putih — jadi setiap galat diratakan jadi teks
   di satu tempat ini. */
export function pesanGalat(error, cadangan) {
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

/* Form gabungan create+edit: dikunci dengan `key` (lihat pemakaian di bawah)
   supaya React membuat instance <form> baru tiap kali baris yang diedit
   berganti atau berpindah ke mode "tambah baru" — cara termurah untuk
   mereset isian tak-terkendali (uncontrolled) tanpa useEffect sinkronisasi. */
function FormIndikator({editing, onCancel, onSaved, onError}) {
  const [saving, setSaving] = useState(false)
  const isEdit = Boolean(editing)

  const submit = async event => {
    event.preventDefault()
    setSaving(true)
    const form = new FormData(event.currentTarget)
    try {
      if (isEdit) await perbaruiIndikatorAdmin(editing.id_indikator, form)
      else await buatIndikatorAdmin(form)
      onSaved()
    } catch (error) {
      onError(pesanGalat(error, 'Gagal menyimpan indikator'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="panel role-form" data-uji="form-indikator" onSubmit={submit}>
      <h3>{isEdit ? `Edit ${editing.id_indikator}` : 'Tambah indikator baru'}</h3>

      <fieldset>
        <legend>Identitas &amp; klasifikasi</legend>
        {/* Saat edit, kategori/nomor dikirim sebagai input hidden, bukan
            disabled: input disabled tidak ikut masuk FormData sama sekali,
            sedangkan backend mewajibkan keduanya untuk memverifikasi bahwa
            id_indikator (primary key) tetap konsisten. */}
        {isEdit ? (
          <div className="form-pair">
            <input type="hidden" name="kategori" value={editing.kategori} readOnly />
            <input type="hidden" name="nomor" value={editing.nomor} readOnly />
            <span className="locked-field">
              {editing.id_indikator} · {editing.kategori}
            </span>
          </div>
        ) : (
          <div className="form-pair">
            <input name="id_indikator" placeholder="mis. ISV-087" required defaultValue="" />
            <select name="kategori" defaultValue="ISV">
              <option value="ISV">ISV</option>
              <option value="IUP">IUP</option>
            </select>
            <input name="nomor" type="number" min="1" placeholder="Nomor urut" required />
          </div>
        )}
        <input
          name="nama_indikator"
          placeholder="Nama indikator"
          required
          defaultValue={editing?.nama_indikator || ''}
        />
        <input name="nama_asli" placeholder="Nama asli (RPJPD)" defaultValue={editing?.nama_asli || ''} />
        <input name="kode_indikator" placeholder="Kode indikator" defaultValue={editing?.kode_indikator || ''} />
        <input name="kelompok" placeholder="Kelompok / pilar" defaultValue={editing?.kelompok || ''} />
        <input
          name="arah_pembangunan"
          placeholder="Arah pembangunan (ISV)"
          defaultValue={editing?.arah_pembangunan || ''}
        />
        <input name="arah_ie" placeholder="Arah Indonesia Emas (IUP)" defaultValue={editing?.arah_ie || ''} />
        <input name="sasaran_visi" placeholder="Sasaran visi" defaultValue={editing?.sasaran_visi || ''} />
        <input name="misi_agenda" placeholder="Misi / agenda" defaultValue={editing?.misi_agenda || ''} />
        <input name="indikator_induk" placeholder="Indikator induk" defaultValue={editing?.indikator_induk || ''} />
        <input name="kelompok_makro" placeholder="Kelompok makro" defaultValue={editing?.kelompok_makro || ''} />
        <input name="satuan" placeholder="Satuan (mis. Persen (%))" defaultValue={editing?.satuan || ''} />
        <label className="checkbox-field">
          <input type="checkbox" name="is_proxy" defaultChecked={editing?.is_proxy || false} />
          <span>Indikator proxy</span>
        </label>
        <input
          name="nama_proxy"
          placeholder="Nama indikator proxy (bila ada)"
          defaultValue={editing?.nama_proxy || ''}
        />
      </fieldset>

      <fieldset>
        <legend>Kepemilikan &amp; ketersediaan</legend>
        <input name="penghasil" placeholder="Penghasil indikator" defaultValue={editing?.penghasil || ''} />
        <input name="kl_pengampu" placeholder="K/L/D/I pengampu" defaultValue={editing?.kl_pengampu || ''} />
        <input name="opd_pengampu" placeholder="OPD pengampu (Kaltara)" defaultValue={editing?.opd_pengampu || ''} />
        <input name="tim_pjk" placeholder="Tim PJK" defaultValue={editing?.tim_pjk || ''} />
        <input name="sumber_data" placeholder="Sumber data" defaultValue={editing?.sumber_data || ''} />
        <input name="frekuensi" placeholder="Frekuensi" defaultValue={editing?.frekuensi || ''} />
        <input
          name="status_ketersediaan"
          placeholder="Status ketersediaan data"
          defaultValue={editing?.status_ketersediaan || ''}
        />
        <input name="status_metadata" placeholder="Status metadata" defaultValue={editing?.status_metadata || ''} />
        <input name="periode_data" placeholder="Periode data" defaultValue={editing?.periode_data || ''} />
        <input
          name="tahun_terakhir"
          type="number"
          placeholder="Tahun data terakhir"
          defaultValue={editing?.tahun_terakhir || ''}
        />
        <input name="status_rpjmd" placeholder="Status RPJMD" defaultValue={editing?.status_rpjmd || ''} />
        <input name="kode_sdgs" placeholder="Kode SDGs" defaultValue={editing?.kode_sdgs || ''} />
        <input name="link_metadata" placeholder="Tautan metadata" defaultValue={editing?.link_metadata || ''} />
        <input name="link_publikasi" placeholder="Tautan publikasi" defaultValue={editing?.link_publikasi || ''} />
        <input name="link_data" placeholder="Tautan data" defaultValue={editing?.link_data || ''} />
        <textarea name="catatan_teknis" placeholder="Catatan teknis" defaultValue={editing?.catatan_teknis || ''} />
      </fieldset>

      <fieldset>
        <legend>Metadata &amp; definisi</legend>
        <textarea name="definisi" placeholder="Definisi" defaultValue={editing?.metadata?.definisi || ''} />
        <textarea
          name="interpretasi"
          placeholder="Interpretasi"
          defaultValue={editing?.metadata?.interpretasi || ''}
        />
        <textarea
          name="rumus"
          placeholder="Rumus (keterangan notasi)"
          defaultValue={editing?.metadata?.rumus || ''}
        />
        <textarea
          name="rumus_mentah"
          placeholder="Rumus perhitungan (mentah)"
          defaultValue={editing?.metadata?.rumus_mentah || ''}
        />
        <input
          name="rumus_latex"
          placeholder="Rumus (LaTeX)"
          defaultValue={editing?.metadata?.rumus_latex || ''}
        />
        <input
          name="halaman_sumber"
          placeholder="Halaman sumber (Buku 1)"
          defaultValue={editing?.metadata?.halaman_sumber || ''}
        />
        <input
          name="sumber_metadata"
          placeholder="Sumber metadata"
          defaultValue={editing?.metadata?.sumber_metadata || ''}
        />
        <input
          name="nama_di_buku1"
          placeholder="Nama di Buku 1"
          defaultValue={editing?.metadata?.nama_di_buku1 || ''}
        />
        <label className="checkbox-field">
          <input
            type="checkbox"
            name="perlu_verifikasi_manual"
            defaultChecked={editing?.metadata?.perlu_verifikasi_manual || false}
          />
          <span>Perlu verifikasi manual</span>
        </label>
      </fieldset>

      <div className="row-actions">
        <button type="button" onClick={onCancel} disabled={saving}>
          Batal
        </button>
        <button type="submit" disabled={saving}>
          {saving ? 'Menyimpan...' : 'Simpan'}
        </button>
      </div>
    </form>
  )
}

export function IndikatorManager() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(null)
  const [creating, setCreating] = useState(false)
  const [message, setMessage] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const result = await daftarIndikatorAdmin({page_size: 200})
      setRows(result.data)
    } catch (error) {
      setMessage(pesanGalat(error, 'Gagal memuat daftar indikator'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const openEdit = async row => {
    try {
      const detail = await detailIndikatorAdmin(row.id_indikator)
      setEditing(detail)
      setCreating(false)
    } catch (error) {
      setMessage(pesanGalat(error, 'Gagal memuat detail indikator'))
    }
  }

  const remove = async row => {
    if (!confirm(`Hapus indikator ${row.id_indikator}? Tindakan ini tidak dapat dibatalkan.`)) return
    try {
      await hapusIndikatorAdmin(row.id_indikator)
      setMessage(`Indikator ${row.id_indikator} dihapus.`)
      load()
    } catch (error) {
      setMessage(pesanGalat(error, 'Gagal menghapus indikator'))
    }
  }

  const closeForm = () => {
    setEditing(null)
    setCreating(false)
  }

  const saved = () => {
    setMessage(editing ? `Indikator ${editing.id_indikator} diperbarui.` : 'Indikator baru ditambahkan.')
    closeForm()
    load()
  }

  return (
    <Panel
      delay={40}
      kicker="Manajemen indikator"
      title="Daftar indikator"
      desc="Buat, ubah, atau hapus indikator dan metadatanya."
      actions={
        <button
          data-uji="tombol-tambah"
          onClick={() => {
            setCreating(true)
            setEditing(null)
          }}
        >
          <Plus size={16} /> Tambah indikator
        </button>
      }
    >
      {message && <p className="form-hint">{message}</p>}

      {(creating || editing) && (
        <FormIndikator
          editing={editing}
          key={editing ? editing.id_indikator : 'baru'}
          onCancel={closeForm}
          onSaved={saved}
          onError={setMessage}
        />
      )}

      {loading ? (
        <p>Memuat...</p>
      ) : rows.length ? (
        <div className="table-scroll">
          <table className="workspace-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Nama</th>
                <th>Kategori</th>
                <th>Kelompok</th>
                <th>Status ketersediaan</th>
                <th>Aksi</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(row => (
                <tr key={row.id_indikator}>
                  <td>
                    <b>{row.id_indikator}</b>
                  </td>
                  <td>{row.nama_indikator}</td>
                  <td>{row.kategori}</td>
                  <td>{row.kelompok || '—'}</td>
                  <td>{row.status_ketersediaan || '—'}</td>
                  <td>
                    <div className="row-actions">
                      <button
                        data-uji={`edit-${row.id_indikator}`}
                        onClick={() => openEdit(row)}
                        aria-label={`Edit ${row.id_indikator}`}
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        data-uji={`hapus-${row.id_indikator}`}
                        onClick={() => remove(row)}
                        disabled={row.punya_nilai}
                        title={
                          row.punya_nilai
                            ? 'Masih punya histori nilai; tidak dapat dihapus'
                            : 'Hapus indikator'
                        }
                        aria-label={`Hapus ${row.id_indikator}`}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState title="Belum ada indikator" desc="Tambahkan indikator pertama lewat tombol di atas." />
      )}
    </Panel>
  )
}
