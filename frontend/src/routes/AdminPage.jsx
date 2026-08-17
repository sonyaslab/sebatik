import {useEffect,useRef,useState} from 'react'
import {
  Activity,AlertTriangle,ArrowLeft,ArrowUpRight,Building2,CheckCircle2,ChevronDown,ChevronLeft,ChevronRight,
  Compass,Database,Download,Eye,EyeOff,FileWarning,Home,Info,ListChecks,LogOut,Mail,MapPin,Menu,Moon,Phone,
  KeyRound,Search,ShieldCheck,Sparkles,Sun,Target,UserRound,X
} from 'lucide-react'
import {
  Area,AreaChart,Bar,BarChart,CartesianGrid,Cell,ComposedChart,Line,LineChart,Pie,PieChart,
  ReferenceLine,ResponsiveContainer,Scatter,ScatterChart,Tooltip,XAxis,YAxis
} from 'recharts'
import {api,qs} from '../api'
import {clearToken,roleLabel,setToken,useProfile,useToken} from '../auth'
import {AuroraField,BatikLayer,WaveDivider,WaveEdge} from '../Brand'
import {chartTheme,useTheme} from '../theme'
import {capaianColor,capaianVar,seriesColor} from '../tokens'
import {
  ChartSkeleton,CountUp,DeltaPill,EmptyState,Panel,Reveal,SECTION_REVEAL,ScrollProgress,SectionHead,
  SkeletonCard,TooltipCard,VizLegend,useScrolled
} from '../ui'
import {fmt,changeNumber,displayedUnit,valueLabel,AnnualChangeTooltip,hasNumber,valueTone,growthTone,softNumber,NAV_LINKS,usePageTitle,authNavItems,CapaianBadge,MetricCard,Topbar,OFFICE_QUERY,OFFICE_EMBED,OFFICE_LINK,FOOTER_CONTACT,SiteFooter,Shell,LoginShell,HERO_PHOTO,YearPicker,HomeHero,HOME_DOORS,HomeDoors,MACRO_INTERVAL,CardRail,MacroCards,regionKey,geoPaths,KaltaraMap} from '../shared'

function SubmissionTable({rows,canDecide=false,onEvidence,onDecision,onCorrect}){
  return <div className="table-scroll">
    <table className="workspace-table">
      <thead>
        <tr>
          <th>Indikator</th><th>Wilayah / pengusul</th><th>Realisasi</th><th>Bukti</th><th>Status</th><th>Keputusan / aksi</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(row=>
          <tr key={row.id}>
            <td><b>{row.id_indikator}</b><small>Usulan #{row.id} · {dateText(row.dibuat_pada)}</small></td>
            <td>{row.wilayah}<small>{row.pengusul}</small></td>
            <td><b>{fmt.format(row.nilai)}</b><small>{row.tahun} · {row.sumber}</small></td>
            <td>
              <button className="evidence-button" onClick={()=>onEvidence(row)}>
                <Eye size={14}/>{row.jumlah_bukti} file
              </button>
            </td>
            <td>
              <span className={`submission-status ${row.status.toLowerCase()}`}>{row.status.replaceAll('_',' ')}</span>
              {row.alasan_verifikasi&&<small>Alasan: {row.alasan_verifikasi}</small>}
            </td>
            <td>
              {canDecide&&row.status==='MENUNGGU_VERIFIKASI'
                ?<div className="row-actions">
                  <button className="approve" onClick={()=>onDecision(row,'DISETUJUI')}>Setujui</button>
                  <button className="reject" onClick={()=>onDecision(row,'DITOLAK')}>Tolak</button>
                </div>
                :onCorrect&&row.status!=='MENUNGGU_VERIFIKASI'
                  ?<button onClick={()=>onCorrect(row)}>Ajukan koreksi</button>
                  :<small>{row.verifikator?`Oleh ${row.verifikator}`:'Menunggu verifikator'}</small>}
            </td>
          </tr>
        )}
      </tbody>
    </table>
    {!rows.length&&<EmptyState icon={ListChecks} compact title="Belum ada usulan" desc="Usulan yang dikirim operator akan tampil di sini."/>}
  </div>
}

/* Bagan alur operator. Mengalir ke bawah, bukan ke samping, karena ia menempati
   kolom sempit di sebelah borang — dan karena membaca langkah dari atas ke
   bawah lebih dekat dengan cara orang membaca daftar tugas.

   Lima langkah berurutan, lalu bercabang dua di ujungnya. Cabang "Ditolak"
   ditutup catatan yang menunjuk balik ke langkah 02, sebab di situlah koreksi
   dimulai — itu satu-satunya bagian alur yang tidak berjalan lurus, jadi ia
   ditandai terpisah dan tidak dibiarkan tersirat. */
const OPERATOR_STEPS=[
  ['Pilih indikator','Tentukan indikator dan tahun data.'],
  ['Isi realisasi','Masukkan nilai dan sumber datanya.'],
  ['Lampirkan bukti','Unggah dokumen pendukung.'],
  ['Kirim','Kirim ke verifikator, lalu pantau status.'],
  ['Verifikasi','Verifikator menilai isian dan bukti.']
]

function OperatorFlow(){
  return <ol className="flow">
    {OPERATOR_STEPS.map(([title,desc],i)=>
      <li className={`flow-step${i===OPERATOR_STEPS.length-1?' is-last':''}`} key={title}>
        <span className="flow-no">{String(i+1).padStart(2,'0')}</span>
        <b>{title}</b>
        <small>{desc}</small>
      </li>
    )}

    <li className="flow-fork">
      <div className="flow-outcome is-rejected">
        <b>Ditolak</b>
        <small>Catatan verifikator terbit.</small>
      </div>
      <div className="flow-outcome is-approved">
        <b>Disetujui</b>
        <small>Data terkunci, tampil di dasbor.</small>
      </div>
    </li>

    <li className="flow-loop">
      <ArrowLeft size={14} aria-hidden="true"/>
      <span>Jika ditolak, ajukan koreksi baru mulai dari langkah <b>02</b>.</span>
    </li>
  </ol>
}

function PasswordResetModal({user,onClose,onSubmit}){
  const [value,setValue]=useState(''),[visible,setVisible]=useState(false),[saving,setSaving]=useState(false)
  const valid=value.length>=12

  useEffect(()=>{
    const close=event=>event.key==='Escape'&&!saving&&onClose()
    addEventListener('keydown',close)
    return()=>removeEventListener('keydown',close)
  },[onClose,saving])

  const submit=async event=>{
    event.preventDefault()
    if(!valid)return
    setSaving(true)
    try{await onSubmit(value)}finally{setSaving(false)}
  }

  return <div className="password-modal-backdrop" onMouseDown={event=>event.target===event.currentTarget&&!saving&&onClose()}>
    <form className="password-modal" role="dialog" aria-modal="true" aria-labelledby="password-modal-title" onSubmit={submit}>
      <header>
        <span className="password-modal-icon"><KeyRound size={21}/></span>
        <div>
          <small>Keamanan akun</small>
          <h2 id="password-modal-title">Atur ulang kata sandi</h2>
          <p>Buat kata sandi awal baru untuk <b>{user.nama}</b> ({user.username}). Pengguna wajib menggantinya saat login.</p>
        </div>
        <button type="button" className="password-modal-close" onClick={onClose} disabled={saving} aria-label="Tutup"><X size={19}/></button>
      </header>
      <label className="password-modal-field">
        <span>Kata sandi baru</span>
        <span className="password-modal-secret">
          <input autoFocus type={visible?'text':'password'} value={value} onChange={event=>setValue(event.target.value)} minLength={12} autoComplete="new-password" placeholder="Minimal 12 karakter" required/>
          <button type="button" onClick={()=>setVisible(current=>!current)} aria-label={visible?'Sembunyikan kata sandi':'Tampilkan kata sandi'}>{visible?<EyeOff size={18}/>:<Eye size={18}/>}</button>
        </span>
      </label>
      <div className={`password-rule ${valid?'is-valid':''}`}><CheckCircle2 size={15}/><span>{valid?'Kata sandi memenuhi syarat':`${value.length}/12 karakter minimum`}</span></div>
      <footer>
        <button type="button" className="password-cancel" onClick={onClose} disabled={saving}>Batal</button>
        <button type="submit" className="password-save" disabled={!valid||saving}>{saving?'Menyimpan...':'Simpan kata sandi'}</button>
      </footer>
    </form>
  </div>
}

export default function AdminPage(){
  const token=useToken()
  const [me,setMe]=useState(null),
    [regions,setRegions]=useState([]),[catalog,setCatalog]=useState([]),[users,setUsers]=useState([]),
    [submissions,setSubmissions]=useState([]),[logs,setLogs]=useState([]),[message,setMessage]=useState(''),
    [evidence,setEvidence]=useState(null),[accountRole,setAccountRole]=useState('OPERATOR'),
    [messageTone,setMessageTone]=useState('warning'),[showPassword,setShowPassword]=useState(false),[passwordUser,setPasswordUser]=useState(null),
    [draft,setDraft]=useState({id_indikator:'',tahun:new Date().getFullYear(),periode:'',nilai:'',sumber:'',catatan:''})

  /* Pesan ruang kerja punya dua nada. `warning` untuk yang perlu dibaca ulang —
     kegagalan, sesi habis, berkas tidak terbuka. `success` untuk tindakan yang
     benar-benar selesai, ditandai centang hijau supaya operator tahu kirimannya
     sudah masuk tanpa harus membaca kalimatnya. */
  const notify=(text,tone='warning')=>{setMessage(text);setMessageTone(tone)}
  const notifyOk=text=>notify(text,'success')

  /* Dipanggil di sini, sebelum cabang-cabang keluar di bawah, supaya urutan
     hook tetap sama pada tiap render — halaman ini punya tiga keadaan (belum
     masuk, memeriksa sesi, ruang kerja) dan ketiganya keluar lebih awal. */
  usePageTitle(token?`Login ${roleLabel(me?.peran)}`:'Login')

  const authFetch=async(path,options={})=>{
    const response=await fetch(path,{...options,headers:{...(options.headers||{}),Authorization:`Bearer ${token}`}})
    if(response.status===401){
      clearToken();setMe(null)
      throw new Error('Sesi berakhir. Silakan login kembali.')
    }
    if(!response.ok)throw new Error(await response.text())
    return response.json()
  }

  const refresh=async(activeToken=token)=>{
    if(!activeToken)return
    const headers={Authorization:`Bearer ${activeToken}`}
    try{
      const profileResponse=await fetch('/api/v1/auth/saya',{headers})
      if(!profileResponse.ok)throw new Error(`AUTH_${profileResponse.status}`)
      const profile=await profileResponse.json()
      const [regionData,catalogData]=await Promise.all([api('/api/v1/wilayah'),api('/api/v1/capaian-explorer')])
      setMe(profile);setRegions(regionData.data);setCatalog(catalogData.indikator)
      const queueResponse=await fetch('/api/v1/admin/usulan',{headers})
      if(!queueResponse.ok)throw new Error(`QUEUE_${queueResponse.status}`)
      const queue=await queueResponse.json()
      setSubmissions(queue.data||[])
      if(profile.peran==='ADMIN'){
        const [accountResponse,logResponse]=await Promise.all([
          fetch('/api/v1/admin/pengguna',{headers}),
          fetch('/api/v1/admin/log',{headers})
        ])
        if(!accountResponse.ok||!logResponse.ok)throw new Error('ADMIN_DATA')
        const accountData=await accountResponse.json(),logData=await logResponse.json()
        setUsers(accountData.data);setLogs(logData.data)
      }
    }catch(error){
      notify('Sesi berakhir. Silakan login kembali.')
      clearToken();setMe(null)
    }
  }

  /* Keluar kini bisa dipicu dari bilah atas, jadi halaman ini harus ikut
     membersihkan dirinya saat token hilang — bukan hanya saat tombol di
     dalamnya yang ditekan. */
  useEffect(()=>{
    if(token)refresh()
    else{setMe(null);setSubmissions([]);setUsers([]);setLogs([]);setEvidence(null)}
  },[token])

  const login=async event=>{
    event.preventDefault()
    const form=new FormData(event.currentTarget)
    const response=await fetch('/api/v1/auth/login',{
      method:'POST',
      headers:{'Content-Type':'application/x-www-form-urlencoded'},
      body:new URLSearchParams({username:form.get('username'),password:form.get('password')})
    })
    const result=await response.json()
    if(!response.ok){notify(result.detail||'Login gagal');return}
    setToken(result.access_token)
    notifyOk('Login berhasil.')
  }

  const loadEvidence=async submission=>{
    try{
      const result=await authFetch(`/api/v1/admin/usulan/${submission.id}/bukti`)
      setEvidence({submission,files:result.data})
    }catch(error){notify(error.message)}
  }

  const openEvidence=async file=>{
    const response=await fetch(`/api/v1/admin/usulan/${evidence.submission.id}/bukti/${file.id}`,{headers:{Authorization:`Bearer ${token}`}})
    if(!response.ok){notify('File bukti tidak dapat dibuka.');return}
    const url=URL.createObjectURL(await response.blob())
    window.open(url,'_blank','noopener,noreferrer')
    setTimeout(()=>URL.revokeObjectURL(url),60000)
  }

  const decide=async(submission,decision)=>{
    let reason=null
    if(decision==='DITOLAK'){reason=prompt('Tuliskan alasan penolakan');if(!reason)return}
    const body=new FormData()
    body.set('keputusan',decision)
    if(reason)body.set('alasan',reason)
    try{
      const result=await authFetch(`/api/v1/admin/usulan/${submission.id}/verifikasi`,{method:'POST',body})
      notifyOk(`Usulan ${result.status.toLowerCase()}.`)
      refresh()
    }catch(error){notify(error.message)}
  }

  if(!token)return <LoginShell>
    <form className="panel role-login" onSubmit={login}>
      <div className="login-head">
        <img className="login-logo" src="/logo-sebatik-monitoring.png" alt="Logo SEBATIK"/>
        <h1>Masuk ke SEBATIK</h1>
        <p>Dasbor Pemantauan Ketersediaan Data ISV-IUP</p>
        <p className="login-org">BPS Provinsi Kalimantan Utara</p>
      </div>

      {message&&<p className="form-error" role="alert">{message}</p>}

      <label className="login-field">
        <span>Nama Pengguna</span>
        <input name="username" autoComplete="username" placeholder="Nama pengguna terdaftar" required autoFocus/>
      </label>

      <label className="login-field">
        <span>Kata Sandi</span>
        {/* Tombol mata duduk di dalam bingkai isian, bukan di sebelahnya, supaya
            lebar kolomnya tetap sama dengan isian di atasnya. */}
        <span className="login-secret">
          <input
            name="password"
            type={showPassword?'text':'password'}
            autoComplete="current-password"
            placeholder="Kata sandi"
            required
          />
          <button
            type="button"
            className="login-peek"
            onClick={()=>setShowPassword(v=>!v)}
            title={showPassword?'Sembunyikan kata sandi':'Tampilkan kata sandi'}
            aria-label={showPassword?'Sembunyikan kata sandi':'Tampilkan kata sandi'}
            aria-pressed={showPassword}
          >
            {showPassword?<EyeOff size={18}/>:<Eye size={18}/>}
          </button>
        </span>
      </label>

      <button className="login-submit">Masuk</button>

      <div className="login-foot">
        <p>Akses terbatas untuk admin dan walidata.</p>
        <p>Belum punya akun? Hubungi Tim Nerwilis BPS Kaltara.</p>
      </div>
    </form>
  </LoginShell>

  if(!me)return <LoginShell>
    <div className="panel role-login session-loading">
      <b>Memeriksa sesi login</b>
      <span>Mohon tunggu sebentar...</span>
    </div>
  </LoginShell>


  const submitValue=async event=>{
    event.preventDefault()
    try{
      const result=await authFetch('/api/v1/admin/usulan',{method:'POST',body:new FormData(event.currentTarget)})
      notifyOk(`Usulan #${result.id} dikirim untuk verifikasi.`)
      setDraft({id_indikator:'',tahun:new Date().getFullYear(),periode:'',nilai:'',sumber:'',catatan:''})
      event.currentTarget.reset()
      refresh()
    }catch(error){notify(error.message)}
  }

  const createAccount=async event=>{
    event.preventDefault()
    try{
      const result=await authFetch('/api/v1/admin/pengguna',{method:'POST',body:new FormData(event.currentTarget)})
      notifyOk(`Akun ${result.username} dibuat.`)
      event.currentTarget.reset()
      refresh()
    }catch(error){notify(error.message)}
  }

  const toggleAccount=async user=>{
    const body=new FormData()
    body.set('aktif',String(!user.aktif))
    try{await authFetch(`/api/v1/admin/pengguna/${user.id}/status`,{method:'PATCH',body});refresh()}
    catch(error){notify(error.message)}
  }

  const resetPassword=async value=>{
    const body=new FormData()
    body.set('password_baru',value)
    try{
      await authFetch(`/api/v1/admin/pengguna/${passwordUser.id}/reset-password`,{method:'POST',body})
      setPasswordUser(null)
      notifyOk('Kata sandi direset dan wajib diganti saat login.')
    }catch(error){notify(error.message)}
  }

  /* Ruang kerja tidak memakai pita kepala halaman. Identitas dan peran sudah
     terbaca di bilah atas, dan pita biru setinggi 300px hanya mendorong isian
     yang justru jadi alasan orang membuka halaman ini. `bare` melewatinya. */
  /* Judul tab sudah dipasang usePageTitle di atas, jadi Shell tidak diberi
     `title` di sini — kalau diberi, ia akan menimpanya dengan nilai yang sama
     lewat jalur kedua. */
  return <Shell active="#login" bare>
    {message&&<div className={`notice ${messageTone}`}>
      {messageTone==='success'?<CheckCircle2 size={17}/>:<Info size={17}/>}
      {message}
    </div>}

    {me?.peran==='ADMIN'&&<>
      <section className="workspace-grid">
        <Reveal as="form" className="panel role-form" onSubmit={createAccount}>
          <SectionHead
            kicker="Manajemen akses"
            title="Tambahkan pengguna"
            desc="Operator dapat ditempatkan di provinsi atau kabupaten/kota. Verifikator hanya di provinsi."
          />
          <input name="username" placeholder="Username" required/>
          <input name="nama" placeholder="Nama lengkap" required/>
          <input name="password" type="password" placeholder="Kata sandi awal (min. 12 karakter)" required/>
          <select name="peran" value={accountRole} onChange={e=>setAccountRole(e.target.value)}>
            <option>OPERATOR</option><option>VERIFIKATOR</option><option>ADMIN</option>
          </select>
          {accountRole!=='ADMIN'&&(accountRole==='VERIFIKATOR'
            ?<><input type="hidden" name="wilayah_kode" value="65"/><div className="locked-field">Provinsi Kalimantan Utara</div></>
            :<select name="wilayah_kode" required>
              <option value="">Pilih wilayah operator</option>
              {regions.map(x=><option value={x.kode} key={x.kode}>{x.nama}</option>)}
            </select>)}
          <button>Buat akun</button>
        </Reveal>

        <Reveal as="section" delay={60} className="panel role-summary">
          <span className="kicker">Ringkasan akses</span>
          <h2>{users.length} akun terdaftar</h2>
          <div className="role-counts">
            {['ADMIN','OPERATOR','VERIFIKATOR'].map(role=>
              <div key={role}><b>{users.filter(u=>u.peran===role).length}</b><span>{role}</span></div>
            )}
          </div>
          <p>Admin dapat membuat akun, mengubah status aktif, mereset kata sandi, melihat bukti, dan memantau antrean.</p>
        </Reveal>
      </section>

      <Panel delay={40} kicker="Pengguna" title="Daftar akun dan akses">
        <div className="table-scroll">
          <table className="workspace-table">
            <thead><tr><th>Pengguna</th><th>Role</th><th>Wilayah</th><th>Status</th><th>Aksi</th></tr></thead>
            <tbody>
              {users.map(user=>
                <tr key={user.id}>
                  <td><b>{user.nama}</b><small>{user.username}</small></td>
                  <td>{user.peran}</td>
                  <td>{user.wilayah||'Seluruh wilayah'}</td>
                  <td><span className={`indicator-state ${user.aktif?'tersedia':'belum-tersedia'}`}>{user.aktif?'Aktif':'Nonaktif'}</span></td>
                  <td>
                    <div className="row-actions">
                      <button onClick={()=>toggleAccount(user)}>{user.aktif?'Nonaktifkan':'Aktifkan'}</button>
                      <button onClick={()=>setPasswordUser(user)}>Reset password</button>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </>}

    {me?.peran==='OPERATOR'&&
      <section className="workspace-grid operator-grid">
        <Reveal as="form" className="panel role-form" onSubmit={submitValue}>
          <SectionHead
            kicker="Input realisasi"
            title="Kirim data indikator"
            desc="Koreksi angka dibuat sebagai usulan baru agar riwayat lama tidak hilang."
          />
          <input type="hidden" name="jenis" value="realisasi"/>
          <select name="id_indikator" value={draft.id_indikator} onChange={e=>setDraft({...draft,id_indikator:e.target.value})} required>
            <option value="">Pilih indikator</option>
            {catalog.map(x=><option value={x.id_indikator} key={x.id_indikator}>{x.kode_indikator} · {x.nama_indikator}</option>)}
          </select>
          <div className="form-pair">
            <input name="tahun" type="number" min="2000" max="2045" value={draft.tahun} onChange={e=>setDraft({...draft,tahun:e.target.value})} required/>
            <select name="periode" value={draft.periode} onChange={e=>setDraft({...draft,periode:e.target.value})}>
              <option value="">Tahunan / tidak berkala</option>
              <option value="1">Semester 1</option>
              <option value="2">Semester 2</option>
            </select>
          </div>
          <div className="form-pair">
            <input name="nilai" type="number" step="any" value={draft.nilai} onChange={e=>setDraft({...draft,nilai:e.target.value})} placeholder="Nilai realisasi" required/>
            <input name="sumber" value={draft.sumber} onChange={e=>setDraft({...draft,sumber:e.target.value})} placeholder="Sumber/instansi pemberi data" required/>
          </div>
          <small className="form-hint">Untuk indikator semesteran, kirim Semester 1 dan Semester 2 sebagai dua usulan. Dashboard otomatis memakai semester terakhir yang telah disetujui.</small>
          <textarea name="catatan" value={draft.catatan} onChange={e=>setDraft({...draft,catatan:e.target.value})} placeholder="Catatan atau alasan koreksi"/>
          <label className="file-field">
            <span>Bukti dukung wajib</span>
            <input name="bukti" type="file" accept=".pdf,.jpg,.jpeg,.png,.xlsx" multiple required/>
            <small>Surat permintaan, balasan OPD, publikasi, atau dokumen pendukung. Maksimal 10 MB/file.</small>
          </label>
          <button>Kirim untuk disetujui</button>
        </Reveal>

        <Reveal as="section" delay={60} className="panel role-summary">
          <span className="kicker">Alur operator</span>
          <h2>Input → bukti → verifikasi</h2>
          <OperatorFlow/>
        </Reveal>
      </section>}

    {(me?.peran==='VERIFIKATOR'||me?.peran==='ADMIN')&&
      <Panel
        delay={40}
        className="verification-queue"
        kicker="Antrean verifikasi"
        title="Data masuk dari seluruh wilayah"
        desc="Periksa angka, sumber, dan bukti sebelum mengambil keputusan."
        actions={<span className="count-pill">{submissions.filter(x=>x.status==='MENUNGGU_VERIFIKASI').length} menunggu</span>}
      >
        <SubmissionTable rows={submissions} canDecide onEvidence={loadEvidence} onDecision={decide}/>
      </Panel>}

    {me?.peran==='OPERATOR'&&
      <Panel delay={40} kicker="Riwayat usulan" title="Status data yang pernah dikirim">
        <SubmissionTable
          rows={submissions}
          onEvidence={loadEvidence}
          onCorrect={row=>{
            setDraft({
              id_indikator:row.id_indikator,tahun:row.tahun,periode:row.periode||'',nilai:row.nilai,sumber:row.sumber,
              catatan:`Koreksi usulan #${row.id}: ${row.alasan_verifikasi||''}`
            })
            scrollTo({top:300,behavior:'smooth'})
          }}
        />
      </Panel>}

    {me?.peran==='ADMIN'&&
      <Panel delay={40} kicker="Audit nilai" title="Jejak perubahan terverifikasi">
        <div className="table-scroll">
          <table className="workspace-table">
            <thead>
              <tr><th>Waktu</th><th>Pengguna</th><th>Indikator</th><th>Nilai lama</th><th>Nilai baru</th><th>Sumber</th></tr>
            </thead>
            <tbody>
              {logs.map(row=>
                <tr key={row.id}>
                  <td>{dateText(row.waktu)}</td>
                  <td>{row.username||'sistem'}</td>
                  <td>{row.id_indikator}</td>
                  <td>{row.nilai_lama??'—'}</td>
                  <td>{row.nilai_baru??'—'}</td>
                  <td>{row.sumber_perubahan}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>}

    {evidence&&
      <div className="evidence-modal" role="dialog" aria-modal="true" onClick={()=>setEvidence(null)}>
        <div onClick={e=>e.stopPropagation()}>
          <header>
            <div>
              <span>Bukti dukung usulan #{evidence.submission.id}</span>
              <h3>{evidence.submission.id_indikator} · {evidence.submission.wilayah}</h3>
            </div>
            <button onClick={()=>setEvidence(null)} aria-label="Tutup">×</button>
          </header>
          {evidence.files.length
            ?evidence.files.map(file=>
              <button className="evidence-file" key={file.id} onClick={()=>openEvidence(file)}>
                <Eye size={18}/>
                <span><b>{file.nama_file}</b><small>{Math.ceil(file.ukuran/1024)} KB · {file.mime_type}</small></span>
              </button>)
            :<EmptyState icon={FileWarning} compact title="Belum ada bukti dukung"/>}
        </div>
      </div>}
    {passwordUser&&<PasswordResetModal user={passwordUser} onClose={()=>setPasswordUser(null)} onSubmit={resetPassword}/>}
  </Shell>
}
