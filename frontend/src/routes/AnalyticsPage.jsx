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

export default function AnalyticsPage(){
  const [cards,setCards]=useState([]),[id,setId]=useState('ISV-01'),[gap,setGap]=useState(null),
    [change,setChange]=useState(null),[rank,setRank]=useState(null),[x,setX]=useState('ISV-04'),
    [y,setY]=useState('ISV-05'),[corr,setCorr]=useState(null)
  const [theme]=useTheme()
  const ct=chartTheme(theme)

  useEffect(()=>{
    api('/api/v1/capaian').then(r=>setCards(r.data))
    api('/api/v1/analitik/peringkat').then(setRank)
  },[])
  useEffect(()=>{
    api(`/api/v1/analitik/gap/${id}`).then(setGap)
    api(`/api/v1/analitik/selisih/${id}`).then(setChange)
  },[id])
  useEffect(()=>{api(`/api/v1/analitik/korelasi?x=${x}&y=${y}`).then(setCorr)},[x,y])

  const opts=cards.map(i=><option key={i.id_indikator} value={i.id_indikator}>{i.id_indikator} · {i.nama_indikator}</option>)
  const upColor=capaianColor('TERCAPAI',theme),downColor=capaianColor('PERLU_PERHATIAN',theme)

  return <Shell
    active="#analitik"
    title="Dasbor Analitik"
    subtitle="Tren, gap target, perbandingan antar-indikator, dan korelasi."
  >
    <div className="notice warning">
      <AlertTriangle size={17}/> Required run-rate adalah ekstrapolasi linear sederhana, bukan proyeksi resmi.
    </div>

    <Panel
      kicker="Tren tahunan"
      title="Tren dan selisih tahunan"
      desc="Warna menunjukkan perbaikan sesuai arah indikator."
      actions={<select className="select" value={id} onChange={e=>setId(e.target.value)} aria-label="Pilih indikator">{opts}</select>}
    >
      <ResponsiveContainer width="100%" height={270}>
        <BarChart data={change?.data||[]} margin={{top:10,right:16,left:0,bottom:0}}>
          <CartesianGrid stroke={ct.grid} vertical={false}/>
          <XAxis dataKey="tahun" tick={{fontSize:11.5,fill:ct.axis}} axisLine={false} tickLine={false}/>
          <YAxis tick={{fontSize:11.5,fill:ct.axis}} axisLine={false} tickLine={false}/>
          <ReferenceLine y={0} stroke={ct.baseline} strokeWidth={1.5}/>
          <Tooltip cursor={{fill:ct.cursor}} content={<TooltipCard/>}/>
          <Bar dataKey="selisih" name="Selisih" radius={[6,6,0,0]} animationDuration={ct.motion}>
            {(change?.data||[]).map((v,i)=><Cell key={i} fill={v.membaik?upColor:downColor}/>)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <VizLegend items={[{label:'Membaik',color:upColor},{label:'Memburuk',color:downColor}]}/>
    </Panel>

    <div className="two-col">
      <Panel delay={40} kicker="Jarak ke target" title="Gap terhadap target">
        <div className="gap-cards">
          <div><span>Target 2029</span><b>{gap?.target_2029??'-'}</b><small>Gap {gap?.gap_2029??'-'}</small></div>
          <div><span>Target 2045</span><b>{gap?.target_2045??'-'}</b><small>Gap {gap?.gap_2045??'-'}</small></div>
          <div>
            <span>Status jalur</span>
            <b>{gap?.status_jalur?.replaceAll('_',' ')||'-'}</b>
            <small>Historis {gap?.laju_historis?.toFixed?.(3)??'-'} / tahun</small>
          </div>
        </div>
      </Panel>
      <Panel delay={80} kicker="Peringkat" title="Perbaikan terbesar">
        <ol className="ranking">
          {rank?.perbaikan_terbesar?.slice(0,5).map(item=>
            <li key={item.id_indikator}><span>{item.nama_indikator}</span><b>{item.skor_perbaikan.toFixed(2)}</b></li>
          )}
        </ol>
      </Panel>
    </div>

    <Panel
      delay={40}
      kicker="Hubungan"
      title="Korelasi antar-indikator"
      desc="Korelasi bukan sebab-akibat; seri pendek tidak layak ditafsirkan."
      actions={
        <div className="select-pair">
          <select className="select" value={x} onChange={e=>setX(e.target.value)} aria-label="Indikator sumbu X">{opts}</select>
          <select className="select" value={y} onChange={e=>setY(e.target.value)} aria-label="Indikator sumbu Y">{opts}</select>
        </div>
      }
    >
      {corr?.n<4
        ?<div className="empty-state">Hasil disembunyikan: hanya {corr?.n||0} tahun berimpitan (minimal 4).</div>
        :<>
          <div className="stat-line">Pearson r = {corr?.pearson} · n = {corr?.n}</div>
          <ResponsiveContainer width="100%" height={290}>
            <ScatterChart margin={{top:10,right:16,left:0,bottom:0}}>
              <CartesianGrid stroke={ct.grid}/>
              <XAxis dataKey="x" name="X" tick={{fontSize:11.5,fill:ct.axis}} axisLine={false} tickLine={false}/>
              <YAxis dataKey="y" name="Y" tick={{fontSize:11.5,fill:ct.axis}} axisLine={false} tickLine={false}/>
              <Tooltip cursor={{strokeDasharray:'4 4',stroke:ct.baseline}} content={<TooltipCard/>}/>
              <Scatter data={corr?.data||[]} fill={seriesColor(0,theme)} animationDuration={ct.motion}/>
            </ScatterChart>
          </ResponsiveContainer>
        </>}
    </Panel>

  </Shell>
}
