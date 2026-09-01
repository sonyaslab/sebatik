import {Download, FileSpreadsheet, Upload} from 'lucide-react'
import {useRef, useState} from 'react'
import {unduhTemplateOperator, unggahRealisasiOperator} from '../../api/endpoints'
import {Panel} from '../../ui'
import {pesanGalatUnggah} from './UnggahExcelPanel'

export function OperatorUploadPanel({onNotify, onSelesai}){
  const inputRef=useRef(null)
  const [sibuk,setSibuk]=useState(false)
  const [hasil,setHasil]=useState(null)

  const unduh=async()=>{
    setSibuk(true)
    try{
      const response=await unduhTemplateOperator()
      if(!response.ok)throw new Error('Template tidak dapat diunduh')
      const url=URL.createObjectURL(await response.blob())
      const link=document.createElement('a')
      link.href=url
      link.download='Template_Unggah_Realisasi_SEBATIK.xlsx'
      link.click()
      URL.revokeObjectURL(url)
    }catch(error){onNotify?.(error.message)}
    finally{setSibuk(false)}
  }

  const unggah=async event=>{
    event.preventDefault()
    const berkas=inputRef.current?.files?.[0]
    if(!berkas)return
    const form=new FormData()
    form.set('berkas',berkas)
    setSibuk(true);setHasil(null)
    try{
      const result=await unggahRealisasiOperator(form)
      setHasil(result)
      onNotify?.(`${result.jumlah_usulan} usulan dari Excel berhasil dikirim untuk verifikasi.`,'success')
      if(inputRef.current)inputRef.current.value=''
      onSelesai?.()
    }catch(error){onNotify?.(pesanGalatUnggah(error,'Unggahan massal gagal'))}
    finally{setSibuk(false)}
  }

  return <Panel
    delay={80}
    className="operator-upload"
    kicker="Input massal"
    title="Unggah realisasi dari Excel"
    desc="Gunakan template baku. Server otomatis mengunci seluruh baris ke wilayah akun Anda dan mengirimnya ke antrean verifikasi."
    actions={<button type="button" className="unggah-tombol" onClick={unduh} disabled={sibuk}>
      <Download size={16}/>Unduh template
    </button>}
  >
    <form className="unggah-form" onSubmit={unggah}>
      <label className="unggah-berkas">
        <span>Workbook realisasi (.xlsx)</span>
        <input ref={inputRef} type="file" accept=".xlsx" required/>
      </label>
      <button className="unggah-tombol" disabled={sibuk}>
        <Upload size={16}/>{sibuk?'Memproses…':'Unggah & kirim'}
      </button>
      <small className="unggah-petunjuk">
        Satu baris untuk satu indikator/tahun/periode. Isi <b>nilai</b> untuk angka atau <b>nilai_teks</b> untuk kategori/rentang.
        Workbook menjadi bukti dukung batch dan setiap baris tetap diperiksa verifikator.
      </small>
    </form>
    {hasil&&<div className="unggah-kabar success" role="status">
      <FileSpreadsheet size={16}/> {hasil.jumlah_usulan} usulan: {hasil.jumlah_angka} angka dan {hasil.jumlah_teks} teks.
    </div>}
  </Panel>
}
