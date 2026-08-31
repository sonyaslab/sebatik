import {useEffect, useState} from 'react'
import {createPortal} from 'react-dom'
import {Info, Pencil, Plus, ShieldCheck, Trash2} from 'lucide-react'
import {EmptyState, Panel} from '../../ui'
import {
  buatIndikatorAdmin,
  daftarIndikatorAdmin,
  detailIndikatorAdmin,
  hapusIndikatorAdmin,
  opsiFormIndikatorAdmin,
  perbaruiIndikatorAdmin,
} from '../../api/endpoints'

const Field = ({label, wide = false, children}) => (
  <label className={`indicator-field${wide ? ' indicator-field-wide' : ''}`}>
    <span>{label}</span>
    {children}
  </label>
)

const FIELD_TERSEMBUNYI = [
  ['nama_asli', 'nama_asli'],
  ['status_rpjmd', 'status_rpjmd'],
  ['kode_sdgs', 'kode_sdgs'],
  ['link_metadata', 'link_metadata'],
  ['link_publikasi', 'link_publikasi'],
  ['link_data', 'link_data'],
  ['kl_pengampu', 'kl_pengampu'],
]

function NilaiLamaTersembunyi({editing}) {
  if (!editing) return null
  return (
    <>
      {FIELD_TERSEMBUNYI.map(([name, key]) => (
        <input key={name} type="hidden" name={name} value={editing[key] || ''} readOnly />
      ))}
      <input type="hidden" name="nama_di_buku1" value={editing.metadata?.nama_di_buku1 || ''} readOnly />
      <input type="hidden" name="halaman_sumber" value={editing.metadata?.halaman_sumber || ''} readOnly />
    </>
  )
}

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
function FormIndikator({editing, options, onCancel, onSaved, onError}) {
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
    <form className="indicator-form" data-uji="form-indikator" onSubmit={submit}>
      <header className="indicator-form-head">
        <div>
          <span className="indicator-form-eyebrow">Form indikator</span>
          <h3>{isEdit ? `Edit ${editing.id_indikator}` : 'Tambah indikator baru'}</h3>
          <p>Lengkapi informasi utama. Kolom bertanda wajib harus diisi.</p>
        </div>
        <ShieldCheck size={24} aria-hidden="true" />
      </header>

      <NilaiLamaTersembunyi editing={editing} />

      <fieldset className="indicator-form-section">
        <legend>Identitas &amp; klasifikasi</legend>
        <div className="indicator-form-grid">
        {/* Saat edit, kategori/nomor dikirim sebagai input hidden, bukan
            disabled: input disabled tidak ikut masuk FormData sama sekali,
            sedangkan backend mewajibkan keduanya untuk memverifikasi bahwa
            id_indikator (primary key) tetap konsisten. */}
        {isEdit ? (
          <div className="indicator-field indicator-field-wide">
            <input type="hidden" name="kategori" value={editing.kategori} readOnly />
            <input type="hidden" name="nomor" value={editing.nomor} readOnly />
            <span>Identitas indikator</span>
            <span className="locked-field">
              {editing.id_indikator} · {editing.kategori}
            </span>
          </div>
        ) : (
          <>
            <Field label="ID indikator *">
              <input name="id_indikator" placeholder="Contoh: ISV-087" required defaultValue="" />
            </Field>
            <Field label="Kategori *">
              <select name="kategori" defaultValue="ISV">
              <option value="ISV">ISV</option>
              <option value="IUP">IUP</option>
              </select>
            </Field>
            <Field label="Nomor urut *">
              <input name="nomor" type="number" min="1" placeholder="87" required />
            </Field>
          </>
        )}
        <Field label="Nama indikator *" wide>
          <input name="nama_indikator" required defaultValue={editing?.nama_indikator || ''} />
        </Field>
        <Field label="Kode indikator">
          <input name="kode_indikator" defaultValue={editing?.kode_indikator || ''} />
        </Field>
        <Field label="Kelompok / pilar *">
          <select name="kelompok" required defaultValue={editing?.kelompok || ''}>
            <option value="">Pilih kelompok / pilar</option>
            {options.kelompok.map(item => <option key={item} value={item}>{item}</option>)}
          </select>
        </Field>
        <Field label="Kelompok makro *">
          <select name="kelompok_makro" required defaultValue={editing?.kelompok_makro || ''}>
            <option value="">Pilih kelompok makro</option>
            {options.kelompok_makro.map(item => <option key={item} value={item}>{item}</option>)}
          </select>
        </Field>
        <Field label="Arah pembangunan (ISV)">
          <input name="arah_pembangunan" defaultValue={editing?.arah_pembangunan || ''} />
        </Field>
        <Field label="Arah Indonesia Emas (IUP)">
          <input name="arah_ie" defaultValue={editing?.arah_ie || ''} />
        </Field>
        <Field label="Sasaran visi">
          <input name="sasaran_visi" defaultValue={editing?.sasaran_visi || ''} />
        </Field>
        <Field label="Misi / agenda">
          <input name="misi_agenda" defaultValue={editing?.misi_agenda || ''} />
        </Field>
        <Field label="Indikator induk">
          <input name="indikator_induk" defaultValue={editing?.indikator_induk || ''} />
        </Field>
        <Field label="Satuan">
          <input name="satuan" placeholder="Contoh: Persen (%)" defaultValue={editing?.satuan || ''} />
        </Field>
        <label className="indicator-toggle indicator-field-wide">
          <input type="checkbox" name="is_proxy" defaultChecked={editing?.is_proxy || false} />
          <span className="indicator-toggle-box" aria-hidden="true" />
          <span><b>Indikator proxy</b><small>Aktifkan jika indikator ini menggunakan indikator pengganti.</small></span>
        </label>
        <Field label="Nama indikator proxy" wide>
          <input name="nama_proxy" placeholder="Isi bila indikator proxy diaktifkan" defaultValue={editing?.nama_proxy || ''} />
        </Field>
        </div>
      </fieldset>

      <fieldset className="indicator-form-section">
        <legend>Kepemilikan &amp; ketersediaan</legend>
        <div className="indicator-form-grid">
          <Field label="Penghasil indikator"><input name="penghasil" defaultValue={editing?.penghasil || ''} /></Field>
          <Field label="OPD pengampu (Kaltara)"><input name="opd_pengampu" defaultValue={editing?.opd_pengampu || ''} /></Field>
          <Field label="Tim PJK"><input name="tim_pjk" defaultValue={editing?.tim_pjk || ''} /></Field>
          <Field label="Sumber data"><input name="sumber_data" defaultValue={editing?.sumber_data || ''} /></Field>
          <Field label="Frekuensi"><input name="frekuensi" defaultValue={editing?.frekuensi || ''} /></Field>
          <Field label="Status ketersediaan"><input name="status_ketersediaan" defaultValue={editing?.status_ketersediaan || ''} /></Field>
          <Field label="Status metadata"><input name="status_metadata" defaultValue={editing?.status_metadata || ''} /></Field>
          <Field label="Periode data"><input name="periode_data" defaultValue={editing?.periode_data || ''} /></Field>
          <Field label="Tahun data terakhir"><input name="tahun_terakhir" type="number" defaultValue={editing?.tahun_terakhir || ''} /></Field>
          <Field label="Catatan teknis" wide><textarea name="catatan_teknis" defaultValue={editing?.catatan_teknis || ''} /></Field>
        </div>
      </fieldset>

      <fieldset className="indicator-form-section">
        <legend>Metadata &amp; definisi</legend>
        <div className="indicator-form-grid">
          <Field label="Definisi" wide><textarea name="definisi" defaultValue={editing?.metadata?.definisi || ''} /></Field>
          <Field label="Interpretasi" wide><textarea name="interpretasi" defaultValue={editing?.metadata?.interpretasi || ''} /></Field>
          <Field label="Rumus dan keterangan notasi" wide><textarea name="rumus" defaultValue={editing?.metadata?.rumus || ''} /></Field>
          <Field label="Rumus perhitungan mentah" wide><textarea name="rumus_mentah" defaultValue={editing?.metadata?.rumus_mentah || ''} /></Field>
          <Field label="Rumus LaTeX"><input name="rumus_latex" defaultValue={editing?.metadata?.rumus_latex || ''} /></Field>
          <Field label="Sumber metadata"><input name="sumber_metadata" defaultValue={editing?.metadata?.sumber_metadata || ''} /></Field>
        </div>
        <div className="manual-verification">
          <Info size={20} aria-hidden="true" />
          <div>
            <label className="indicator-toggle">
          <input
            type="checkbox"
            name="perlu_verifikasi_manual"
            defaultChecked={editing?.metadata?.perlu_verifikasi_manual || false}
          />
              <span className="indicator-toggle-box" aria-hidden="true" />
              <span><b>Perlu verifikasi manual</b></span>
            </label>
            <p>Tandai bila definisi, sumber, atau rumus belum diperiksa petugas dan belum boleh dianggap metadata final.</p>
          </div>
        </div>
      </fieldset>

      <div className="indicator-form-actions">
        <button className="indicator-cancel" type="button" onClick={onCancel} disabled={saving}>
          Batal
        </button>
        <button className="indicator-save" type="submit" disabled={saving}>
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
  const [options, setOptions] = useState({kelompok: [], kelompok_makro: []})
  const [pendingDelete, setPendingDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [result, formOptions] = await Promise.all([
        daftarIndikatorAdmin({page_size: 200}),
        opsiFormIndikatorAdmin(),
      ])
      setRows(result.data)
      setOptions(formOptions)
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

  const remove = async () => {
    if (!pendingDelete) return
    const row = pendingDelete
    setDeleting(true)
    try {
      // Backend hanya menerima penghapusan yang membawa persetujuan eksplisit.
      await hapusIndikatorAdmin(row.id_indikator, true)
      setMessage(`Indikator ${row.id_indikator} dihapus.`)
      setPendingDelete(null)
      load()
    } catch (error) {
      setMessage(pesanGalat(error, 'Gagal menghapus indikator'))
    } finally {
      setDeleting(false)
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
          className="indicator-add-button"
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
          options={options}
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
                        type="button"
                        className="indicator-edit-button"
                        data-uji={`edit-${row.id_indikator}`}
                        onClick={() => openEdit(row)}
                        aria-label={`Edit ${row.id_indikator}`}
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        type="button"
                        className="indicator-delete-button"
                        data-uji={`hapus-${row.id_indikator}`}
                        onClick={event => {
                          event.preventDefault()
                          event.stopPropagation()
                          setPendingDelete(row)
                        }}
                        title="Hapus indikator"
                        aria-label={`Hapus ${row.id_indikator}`}
                      >
                        <Trash2 size={16} aria-hidden="true" />
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

      {pendingDelete && createPortal(
        <div className="indicator-delete-notification" role="presentation">
          <section className="indicator-delete-dialog" role="alertdialog" aria-labelledby="indicator-delete-title" aria-describedby="indicator-delete-description">
            <span className="indicator-delete-icon"><Trash2 size={22} /></span>
            <div className="indicator-delete-copy">
              <h2 id="indicator-delete-title">Hapus indikator?</h2>
              <p id="indicator-delete-description">
              Indikator <b>{pendingDelete.id_indikator}</b> — {pendingDelete.nama_indikator} beserta
              histori nilai dan usulan terkait akan dihapus permanen.
              </p>
            </div>
            <div className="indicator-delete-actions">
              <button type="button" className="indicator-cancel" onClick={() => setPendingDelete(null)} disabled={deleting}>Batal</button>
              <button type="button" className="indicator-confirm-delete" onClick={remove} disabled={deleting}>
                {deleting ? 'Menghapus...' : 'Ya, hapus'}
              </button>
            </div>
          </section>
        </div>,
        document.body,
      )}
    </Panel>
  )
}
