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

export default function DetailPage({id}){
  const [item,setItem]=useState(null)
  const [theme]=useTheme()
  const ct=chartTheme(theme)

  useEffect(()=>{api(`/api/v1/indikator/${id}/detail`).then(setItem)},[id])

  if(!item)return <Shell active="#capaian" title="Detail Indikator" subtitle="Memuat rincian indikator...">
    <div className="panel"><ChartSkeleton height={300}/></div>
  </Shell>

  const years=[...new Set(item.nilai.map(x=>x.tahun))].sort()
  const chart=years.map(t=>({
    tahun:t,
    realisasi:item.nilai.find(x=>x.tahun===t&&x.jenis==='realisasi')?.nilai,
    target:item.nilai.find(x=>x.tahun===t&&x.jenis==='target')?.nilai
  }))

  return <Shell
    active="#capaian"
    title="Detail Indikator"
    subtitle={`${item.id_indikator} · ${item.nama_indikator}`}
  >
    <a href="#capaian" className="back"><ArrowLeft size={15}/> Kembali ke daftar</a>

    <Reveal as="section" className="panel detail-head">
      <div>
        <span className={`category ${item.kategori.toLowerCase()}`}>{item.kategori}</span>
        <h2>{item.nama_indikator}</h2>
        <p>{item.kelompok} · Arah baik {item.arah_baik}</p>
      </div>
      <CapaianBadge status={item.status_capaian}/>
    </Reveal>

    <Panel delay={60} kicker="Seri waktu" title="Realisasi dan target">
      <ResponsiveContainer width="100%" height={340}>
        {/* Perlakuan sama dengan grafik utama di penjelajah indikator: capaian
            berisi, acuan tipis, tidak ada garis putus-putus. */}
        <ComposedChart data={chart} margin={{top:12,right:20,left:0,bottom:4}}>
          <defs>
            <linearGradient id="grad-detail" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={seriesColor(0,theme)} stopOpacity={.26}/>
              <stop offset="100%" stopColor={seriesColor(0,theme)} stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid stroke={ct.grid} vertical={false}/>
          <XAxis dataKey="tahun" tick={{fontSize:11.5,fill:ct.axis}} axisLine={false} tickLine={false}/>
          <YAxis tick={{fontSize:11.5,fill:ct.axis}} axisLine={false} tickLine={false}/>
          <Tooltip cursor={{stroke:ct.baseline,strokeWidth:1}} content={<TooltipCard formatter={v=>valueLabel(v,null,item.satuan)}/>}/>
          <Line dataKey="target" name="Target" type="monotone" stroke={seriesColor(2,theme)}
            strokeWidth={1.75} dot={{r:2.5,fill:ct.surface,stroke:seriesColor(2,theme),strokeWidth:1.75}}
            activeDot={{r:5,strokeWidth:2,stroke:ct.surface}} animationDuration={ct.motion}/>
          <Area dataKey="realisasi" name="Realisasi" type="monotone" stroke={seriesColor(0,theme)} strokeWidth={2.75}
            fill="url(#grad-detail)"
            dot={{r:3.5,fill:ct.surface,stroke:seriesColor(0,theme),strokeWidth:2}}
            activeDot={{r:6,strokeWidth:2.5,stroke:ct.surface}} animationDuration={ct.motion}/>
        </ComposedChart>
      </ResponsiveContainer>
      <VizLegend items={[
        {label:'Realisasi',color:seriesColor(0,theme),shape:'line'},
        {label:'Target',color:seriesColor(2,theme),shape:'line'}
      ]}/>
    </Panel>

    <div className="detail-columns">
      <Panel delay={40} kicker="Dokumentasi" title="Metadata indikator">
        {[
          ['Definisi',item.metadata?.definisi],
          ['Rumus perhitungan',item.metadata?.rumus_mentah],
          ['Interpretasi',item.metadata?.interpretasi],
          ['Sumber data',item.metadata?.sumber_data],
          ['Frekuensi',item.metadata?.frekuensi]
        ].map(([k,v])=><details key={k}><summary>{k}</summary><p>{v||'Belum tersedia'}</p></details>)}
      </Panel>

      <Panel delay={80} className="governance" kicker="Tanggung jawab" title="Tata kelola">
        <dl>
          <dt>Penghasil</dt><dd>{item.penghasil||'-'}</dd>
          <dt>K/L pengampu</dt><dd>{item.kl_pengampu||'-'}</dd>
          <dt>OPD penanggung jawab</dt><dd>{item.opd_penanggung_jawab||'-'}</dd>
          <dt>Tim PJK</dt><dd>{item.tim_pjk||'-'}</dd>
        </dl>
        {[
          ['Metadata',item.link_metadata],
          ['Publikasi',item.link_publikasi],
          ['Data mentah',item.link_data]
        ].filter(x=>x[1]).map(x=>
          <a key={x[0]} href={x[1]} target="_blank" rel="noreferrer">{x[0]} (tautan luar)</a>
        )}
      </Panel>
    </div>

    <Panel
      delay={40}
      kicker="Rincian angka"
      title="Tabel nilai"
      actions={<a className="button-link" href={`/api/v1/indikator/${id}/unduh.csv`}><Download size={15}/> Unduh indikator</a>}
    >
      <div className="table-scroll">
        <table className="value-table">
          <thead><tr><th>Tahun</th><th>Jenis</th><th>Nilai</th><th>Sumber</th></tr></thead>
          <tbody>
            {item.nilai.map((x,i)=>
              <tr key={i}>
                <td className="mono">{x.tahun}</td>
                <td>{x.jenis}</td>
                <td className="mono">{x.nilai??'Belum Tersedia'}</td>
                <td>{x.sumber_sheet}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Panel>
  </Shell>
}
