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

const dateText=value=>{
  if(!value)return '—'
  const parsed=new Date(value.includes('T')?value:value.replace(' ','T')+'Z')
  return Number.isNaN(parsed.getTime())?value:parsed.toLocaleDateString('id-ID',{day:'2-digit',month:'long',year:'numeric'})
}

function MetadataModal({item,onClose}){
  useEffect(()=>{
    const close=e=>e.key==='Escape'&&onClose()
    addEventListener('keydown',close)
    return()=>removeEventListener('keydown',close)
  },[onClose])
  if(!item)return null
  const meta=item.metadata||{}
  const years=[...new Set((item.nilai||[]).map(x=>x.tahun))].sort((a,b)=>a-b)
  const value=(year,kind)=>item.nilai.find(x=>x.tahun===year&&x.jenis===kind)
  return <div className="metadata-modal-backdrop" role="presentation" onMouseDown={e=>e.target===e.currentTarget&&onClose()}>
    <section className="metadata-modal" role="dialog" aria-modal="true" aria-labelledby="metadata-title">
      <header>
        <div><span>{item.kategori} · {item.id_indikator}</span><h2 id="metadata-title">{item.nama_indikator}</h2></div>
        <button onClick={onClose} aria-label="Tutup metadata"><X size={20}/></button>
      </header>
      {!item.metadata_tersedia&&<div className="notice warning"><Info size={17}/>Metadata RPJPD belum tersedia untuk indikator ini.</div>}
      <div className="metadata-grid">
        {[
          ['Definisi',meta.definisi],['Interpretasi',meta.interpretasi],
          ['Sumber data',meta.sumber_data],['Frekuensi',meta.frekuensi]
        ].map(([label,text])=><article key={label}><small>{label}</small><p>{text||'Belum tersedia'}</p></article>)}
      </div>
      <article className="formula-card"><small>Rumus perhitungan</small>
        {meta.rumus_latex?<div className="formula-latex">{meta.rumus_latex}</div>:<pre>{meta.rumus_mentah||'Belum tersedia'}</pre>}
        <em>Sumber metadata: {meta.sumber_metadata||'Belum tersedia'}</em>
      </article>
      <div className="table-scroll metadata-values"><table className="value-table"><thead><tr><th>Tahun</th><th>Realisasi</th><th>Target</th><th>Satuan/catatan</th></tr></thead>
        <tbody>{years.map(year=>{const actual=value(year,'realisasi'),target=value(year,'target');return <tr key={year}><td>{year}</td><td>{valueLabel(actual?.nilai,actual?.nilai_teks,item.satuan)}</td><td>{valueLabel(target?.nilai,target?.nilai_teks,item.satuan)}</td><td>{item.satuan||actual?.satuan_catatan||target?.satuan_catatan||'—'}</td></tr>})}</tbody>
      </table>{!years.length&&<p className="empty-inline">Data angka realisasi dan target belum tersedia.</p>}</div>
    </section>
  </div>
}

export default function ValidityPage(){
  const [data,setData]=useState(null),[region,setRegion]=useState('65'),[query,setQuery]=useState(''),[error,setError]=useState(''),[metadata,setMetadata]=useState(null)
  /* Dibaca dari sumber bersama, bukan langsung dari localStorage: saat pengguna
     menekan Keluar di bilah atas, tabel ini ikut dimuat ulang sebagai tamu. */
  const token=useToken()

  useEffect(()=>{
    let cancelled=false
    const timer=setTimeout(async()=>{
      try{
        const path='/api/v1/validitas?'+qs({wilayah_kode:region,q:query})
        let response=await fetch(path,{headers:token?{Authorization:`Bearer ${token}`}:{}})
        if(response.status===401&&token){clearToken();response=await fetch(path)}
        if(!response.ok)throw new Error(`API gagal (${response.status})`)
        const result=await response.json()
        if(!cancelled){setData(result);setError('')}
      }catch(e){if(!cancelled)setError(e.message)}
    },180)
    return()=>{cancelled=true;clearTimeout(timer)}
  },[region,query,token])

  const viewMetadata=async row=>{
    try{setMetadata({id_indikator:row.id_indikator,nama_indikator:row.nama_indikator,loading:true});setMetadata(await api(`/api/v1/beranda-indikator/${row.id_indikator}/metadata`))}
    catch(e){setMetadata(null);setError(`Metadata tidak dapat dimuat: ${e.message}`)}
  }

  return <Shell
    active="#validitas"
    title="Validitas"
    subtitle="Status verifikasi, pembaruan, dan metadata setiap indikator menurut wilayah."
  >
    {error&&<div className="error"><AlertTriangle size={18}/>{error}</div>}

    <Reveal as="section" className="panel validity-panel">
      <div className="validity-toolbar">
        <label className="field">
          <span>Wilayah</span>
          <select value={region} onChange={e=>setRegion(e.target.value)}>
            {(data?.wilayah_opsi||[]).map(x=><option value={x.kode} key={x.kode}>{x.nama}</option>)}
          </select>
        </label>
        <label className="search">
          <Search size={17}/>
          <input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Cari nama atau kode indikator..." aria-label="Cari indikator"/>
        </label>
      </div>

      <div className="table-scroll">
        <table className="validity-table">
          <thead>
            <tr>
              <th>Nama indikator</th><th>Instansi pengampu</th><th>Validasi</th><th>Update</th>
              <th>Status indikator</th><th>Metadata</th>
            </tr>
          </thead>
          <tbody>
            {(data?.data||[]).map(x=>
              <tr key={x.id_indikator}>
                <td><b>{x.nama_indikator}</b><small>{x.id_indikator}</small></td>
                <td>{x.instansi_pengampu}</td>
                <td>
                  <span className={`validation-state ${x.terverifikasi_pada?'verified':'waiting'}`}>
                    <i/>
                    {x.terverifikasi_pada
                      ?<span>Terverifikasi<small>{dateText(x.terverifikasi_pada)}</small></span>
                      :<span>Belum diverifikasi<small>Menunggu data wilayah</small></span>}
                  </span>
                </td>
                <td>
                  <span className="update-cell">
                    {x.terverifikasi_pada
                      ?<>Terakhir diperbarui {dateText(x.terverifikasi_pada)}<small>oleh {x.update_oleh}</small></>
                      :'Belum ada pembaruan'}
                  </span>
                </td>
                <td>
                  <span className={`indicator-state ${x.status_indikator.toLowerCase().replaceAll(' ','-')}`}>
                    {x.status_indikator}
                  </span>
                </td>
                <td>
                  <button className="metadata-eye" onClick={()=>viewMetadata(x)} title={x.metadata_tersedia?'Lihat metadata dan tabel nilai':'Metadata belum tersedia'} aria-label={`Lihat metadata ${x.nama_indikator}`}>
                    <Eye size={17}/>
                  </button>
                </td>
              </tr>
            )}
          </tbody>
        </table>
        {data&&!data.data?.length&&
          <EmptyState icon={Search} compact title="Tidak ada indikator yang cocok" desc="Ubah kata kunci atau pilih wilayah lain."/>}
      </div>
    </Reveal>
    {metadata?.loading&&<div className="metadata-modal-backdrop"><div className="metadata-loading"><ChartSkeleton height={180}/></div></div>}
    {metadata&&!metadata.loading&&<MetadataModal item={metadata} onClose={()=>setMetadata(null)}/>}
  </Shell>
}
