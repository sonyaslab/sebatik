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
import {api,qs} from './api'
import {clearToken,roleLabel,setToken,useProfile,useToken} from './auth'
import {AuroraField,BatikLayer,WaveDivider,WaveEdge} from './Brand'
import {chartTheme,useTheme} from './theme'
import {capaianColor,capaianVar,seriesColor} from './tokens'
import {
  ChartSkeleton,CountUp,DeltaPill,EmptyState,Panel,Reveal,SECTION_REVEAL,ScrollProgress,SectionHead,
  SkeletonCard,TooltipCard,VizLegend,useScrolled
} from './ui'

const fmt=new Intl.NumberFormat('id-ID')
const changeNumber=new Intl.NumberFormat('id-ID',{minimumFractionDigits:2,maximumFractionDigits:2})
const displayedUnit=unit=>{
  if(!unit||/^indeks\b/i.test(unit))return ''
  if(/persen|\(%\)|% PDRB/i.test(unit))return '%'
  return unit
}
const valueLabel=(value,text,unit)=>{
  if(value===null||value===undefined)return text||'Belum tersedia'
  const suffix=displayedUnit(unit)
  return `${fmt.format(value)}${suffix==='%'?'%':suffix?` ${suffix}`:''}`
}

function AnnualChangeTooltip({active,payload,arahTarget}){
  if(!active||!payload?.length)return null
  const item=payload[0]?.payload
  if(!item||item.previousValue===null||item.previousValue===undefined)return null
  const pointChange=item.nilai-item.previousValue
  const movement=pointChange>0?'Naik':pointChange<0?'Turun':'Tetap'
  const targetRelation=(arahTarget==='TURUN'?item.growth<=0:item.growth>=0)
    ?'searah dengan target 2045'
    :'berlawanan arah dengan target 2045'
  const signedGrowth=`${item.growth>0?'+':item.growth<0?'−':''}${changeNumber.format(Math.abs(item.growth))}%`
  return <div className="viz-tooltip annual-change-tooltip" role="tooltip">
    <strong>{item.tahun} · realisasi {changeNumber.format(item.nilai)}</strong>
    <span>{movement} {changeNumber.format(Math.abs(pointChange))} poin dari {item.previousYear} ({changeNumber.format(item.previousValue)})</span>
    <span>{signedGrowth} · {targetRelation}</span>
  </div>
}
/* Ukuran angka sorotan dipasang untuk angka. Ketika yang tampil justru kalimat
   — "Belum tersedia" — ukuran itu membuatnya berteriak lebih keras daripada
   angka yang benar-benar ada di kartu sebelahnya. Penanda ini dipakai untuk
   menurunkan ukurannya, bukan untuk menyembunyikannya. */
const hasNumber=value=>value!==null&&value!==undefined
const valueTone=value=>hasNumber(value)?'':' is-empty'

/* Warna pertumbuhan pada kartu tahun: naik hijau, turun merah, datar netral.
   Perlu dicatat bahwa ini mewarnai ARAH ANGKA, bukan baik-buruknya keadaan.
   Pada indikator yang arah baiknya menurun — tingkat kemiskinan, pengangguran,
   rasio gini — kenaikan angka justru kabar buruk tetapi tetap tampil hijau.
   Basis data menyimpan `arah_baik`/`arah_target` bila suatu saat pewarnaan
   ingin diikatkan ke makna, bukan ke arah. */
const growthTone=growth=>growth===null||growth===0?'growth-flat':growth>0?'growth-up':'growth-down'
/* Format angka animasi: pertahankan satu desimal supaya nilai persen tidak
   kehilangan ketelitian saat dihitung naik. */
const softNumber=v=>fmt.format(Number(Number(v).toFixed(1)))

/* Peta rute -> label, ikon, dan deskripsi singkat untuk navigasi. */
const NAV_LINKS=[
  ['#beranda','Beranda',Home],
  ['#indikator','Indikator',Compass],
  ['#capaian','Capaian',Target],
  ['#insight','Insight',Sparkles],
  ['#validitas','Validitas',ShieldCheck]
]

/* Slot terakhir navigasi mengikuti status masuk.

   Sebelum ini slot tersebut memuat satu kendali saja: "Masuk" ketika belum
   masuk, "Keluar" ketika sudah. Penggabungan itu menutup satu-satunya jalan
   kembali — begitu pengguna yang sudah masuk membuka Beranda atau Indikator,
   tidak ada lagi tautan menuju ruang kerjanya, dan satu-satunya kendali yang
   tersisa justru mengakhiri sesinya. Ruang kerjanya masih hidup di #login,
   tetapi hanya bisa dicapai dengan mengetik sendiri di bilah alamat.

   Karena itu keadaan "sudah masuk" kini memuat dua kendali terpisah: jalan
   kembali ke ruang kerja, dan keluar. Keduanya perbuatan yang berbeda, jadi
   memang tidak sepantasnya berbagi satu tombol. */
/* Judul tab memuat nama fitur saja — "Beranda", "Indikator", "Login Admin".
   Sebelumnya ia merangkai nama fitur dengan nama panjang sistem, dan di lebar
   tab yang biasa hasilnya terpotong justru pada bagian yang membedakan satu
   tab dari tab lain. Nama sistem sudah dibawa favicon di sebelahnya.

   Judul dipasang oleh satu pemilik saja. `undefined` berarti "aku tidak
   mengatur judul", bukan "kosongkan judulnya" — tanpa pembedaan itu, <Shell>
   yang dipakai tanpa `title` akan menimpa judul yang baru saja dipasang
   halaman di atasnya, dan ruang kerja kehilangan sebutan perannya. */
function usePageTitle(title){
  useEffect(()=>{
    if(title===undefined)return
    document.title=title||'SEBATIK'
  },[title])
}

const authNavItems=(token,profile)=>token
  ? [
      {hash:'#login',label:roleLabel(profile?.peran),icon:UserRound,logout:false},
      {hash:'#beranda',label:'Keluar',icon:LogOut,logout:true}
    ]
  : [{hash:'#login',label:'Masuk',icon:UserRound,logout:false}]

function CapaianBadge({status}){
  const key=status||'BELUM_ADA_DATA'
  return <span className="capaian-badge" style={{'--tone':capaianVar(key)}}>{key.replaceAll('_',' ')}</span>
}

/* ==========================================================================
   Kartu metrik
   ========================================================================== */

function MetricCard({icon:Icon,label,value,note,tone='var(--series-1)',meter=null,index=0}){
  const [mounted,setMounted]=useState(false)
  useEffect(()=>{const timer=setTimeout(()=>setMounted(true),120+index*80);return()=>clearTimeout(timer)},[index])
  return <Reveal as="article" delay={index*70} className="metric-card" style={{'--tone':tone,'--i':index}}>
    <div className="metric-top"><span className="metric-icon"><Icon size={20}/></span></div>
    <p className="metric-label">{label}</p>
    <strong className="metric-value">
      {typeof value==='number'?<CountUp value={value} format={v=>fmt.format(Math.round(v))}/>:value}
    </strong>
    <span className="metric-note">{note}</span>
    {meter!==null&&<div className="metric-meter" role="presentation"><i style={{width:`${mounted?meter:0}%`}}/></div>}
  </Reveal>
}

/* ==========================================================================
   Kerangka halaman
   ========================================================================== */

function Topbar({active}){
  const [theme,toggle]=useTheme()
  const [open,setOpen]=useState(false)
  const scrolled=useScrolled()
  const token=useToken()
  const profile=useProfile()
  const authItems=authNavItems(token,profile)
  const onAuth=item=>{if(item.logout)clearToken();setOpen(false)}
  /* Hanya tautan yang benar-benar menuju sebuah halaman yang boleh ditandai
     aktif. "Keluar" adalah tindakan, bukan tujuan — ia tidak pernah aktif. */
  const isAuthActive=item=>!item.logout&&active===item.hash

  useEffect(()=>{
    const close=()=>setOpen(false)
    addEventListener('hashchange',close)
    return()=>removeEventListener('hashchange',close)
  },[])

  useEffect(()=>{
    if(!open)return
    const onKey=event=>{if(event.key==='Escape')setOpen(false)}
    addEventListener('keydown',onKey)
    document.body.style.overflow='hidden'
    return()=>{removeEventListener('keydown',onKey);document.body.style.overflow=''}
  },[open])

  return <>
    <header className="topbar" data-scrolled={String(scrolled)}>
      <a className="brand" href="#beranda" aria-label="SEBATIK — kembali ke beranda">
        <span className="brand-mark"><img src="/logo-sebatik-monitoring.png" alt=""/></span>
        <span className="brand-name"><b>SEBATIK</b><small>BPS Provinsi Kalimantan Utara</small></span>
      </a>

      <nav className="nav-desktop" aria-label="Navigasi utama">
        {NAV_LINKS.map(([hash,label])=>
          <a key={hash} href={hash} className={active===hash?'active':''} aria-current={active===hash?'page':undefined}>
            {label}
          </a>
        )}
        {authItems.map(item=>
          <a
            key={item.label}
            href={item.hash}
            onClick={()=>onAuth(item)}
            className={`nav-auth${item.logout?' is-out':''}${isAuthActive(item)?' active':''}`}
            aria-current={isAuthActive(item)?'page':undefined}
          >
            <item.icon size={16} aria-hidden="true"/>{item.label}
          </a>
        )}
      </nav>

      <div className="topbar-tools">
        <button
          className="icon-btn"
          onClick={toggle}
          title={theme==='dark'?'Beralih ke mode terang':'Beralih ke mode gelap'}
          aria-label={theme==='dark'?'Beralih ke mode terang':'Beralih ke mode gelap'}
        >
          {theme==='dark'?<Sun size={18}/>:<Moon size={18}/>}
        </button>
        <button
          className="icon-btn nav-toggle"
          onClick={()=>setOpen(v=>!v)}
          aria-label={open?'Tutup menu':'Buka menu'}
          aria-expanded={open}
        >
          {open?<X size={19}/>:<Menu size={19}/>}
        </button>
      </div>

      <ScrollProgress/>
    </header>

    <div className="nav-drawer" data-open={String(open)} aria-hidden={!open}>
      <div className="nav-drawer-scrim" onClick={()=>setOpen(false)}/>
      <nav className="nav-drawer-panel" aria-label="Navigasi seluler">
        {NAV_LINKS.map(([hash,label,Icon],index)=>
          <a
            key={hash}
            href={hash}
            style={{'--i':index}}
            className={active===hash?'active':''}
            aria-current={active===hash?'page':undefined}
            onClick={()=>setOpen(false)}
          >
            <span><Icon size={18}/>{label}</span>
            <ChevronRight size={16}/>
          </a>
        )}
        {authItems.map((item,i)=>
          <a
            key={item.label}
            href={item.hash}
            style={{'--i':NAV_LINKS.length+i}}
            className={`nav-auth${item.logout?' is-out':''}${isAuthActive(item)?' active':''}`}
            aria-current={isAuthActive(item)?'page':undefined}
            onClick={()=>onAuth(item)}
          >
            <span><item.icon size={18}/>{item.label}</span>
            <ChevronRight size={16}/>
          </a>
        )}
        <p className="nav-drawer-note">
          Dasbor pemantauan capaian indikator ISV–IUP, RPJPN 2025–2045.
        </p>
      </nav>
    </div>
  </>
}

/* Peta kantor. Sengaja memakai sematan Google tanpa kunci API supaya tidak
   ada rahasia yang perlu disimpan di frontend. Alamat dan tautan di bawahnya
   berdiri sendiri, jadi ketika jaringan kantor memblokir domain Google
   informasinya tetap lengkap — bingkai kosong, isi tidak hilang. */
const OFFICE_QUERY='Badan Pusat Statistik Provinsi Kalimantan Utara, Jl. Jelarai Raya, Tanjung Selor Hilir'
const OFFICE_EMBED=`https://maps.google.com/maps?q=${encodeURIComponent(OFFICE_QUERY)}&z=16&output=embed`
const OFFICE_LINK=`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(OFFICE_QUERY)}`

const FOOTER_CONTACT=[
  [MapPin,'Alamat','Jl. Jelarai Raya RT 75 RW 28, Tanjung Selor Hilir, Bulungan 77212'],
  [Phone,'Telepon','(0552) 2033254 · WhatsApp 0822-5442-6005']
]

/* Panel alamat dan peta hanya dipasang di beranda — di sana ia berperan sebagai
   penutup identitas. Halaman lain cukup memakai satu baris hak cipta supaya
   kaki halaman tidak mengulang informasi yang sama di setiap layar. */
function SiteFooter({office=false}){
  return <footer className={`site-footer${office?'':' is-slim'}`}>
    {office&&<div className="footer-panel">
      <div className="footer-info">
        <h2>Badan Pusat Statistik<em>Provinsi Kalimantan Utara</em></h2>

        <dl className="footer-contact">
          {FOOTER_CONTACT.map(([Icon,label,value])=>
            <div key={label}>
              <dt><Icon size={17}/><span>{label}</span></dt>
              <dd>{value}</dd>
            </div>
          )}
          <div>
            <dt><Mail size={17}/><span>Surel</span></dt>
            <dd><a href="mailto:bps6500@bps.go.id">bps6500@bps.go.id</a></dd>
          </div>
        </dl>
      </div>

      <div className="footer-map">
        <iframe
          src={OFFICE_EMBED}
          title="Peta lokasi kantor BPS Provinsi Kalimantan Utara"
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
          allowFullScreen
        />
        <a className="footer-map-link" href={OFFICE_LINK} target="_blank" rel="noreferrer">
          <span><b>Kantor BPS Kalimantan Utara</b><small>Tanjung Selor, Bulungan</small></span>
          <ArrowUpRight size={17}/>
        </a>
      </div>
    </div>}

    <div className="footer-base">
      <small>© {new Date().getFullYear()} Tim Kerja ISV-IUP BPS Provinsi Kalimantan Utara · Hak Cipta Dilindungi.</small>
    </div>
  </footer>
}

/* Kepala halaman sengaja hanya memuat satu kalimat. Nama fiturnya sudah
   terbaca di navigasi dan di judul tab, jadi mengulangnya sebagai judul besar
   cuma menambah tinggi tanpa menambah keterangan. Yang tersisa adalah kalimat
   yang benar-benar menjelaskan isi halaman, diberi ruang untuk bernapas.
   Properti `title` tetap diterima karena dipakai untuk judul dokumen. */
function Shell({active,title,subtitle,bare=false,children}){
  usePageTitle(title)

  if(bare)return <div className="app">
    <div className="shell">
      <Topbar active={active}/>
      <main className="bare-main">{children}</main>
    </div>
    <SiteFooter/>
  </div>

  return <div className="app">
    <div className="shell">
      <Topbar active={active}/>
      <header className="hero">
        <AuroraField/>
        <BatikLayer opacity={.09} drift/>
        {/* Kalimat ini adalah judul halaman yang sebenarnya — karena itu ia
            tetap <h1>, meski tampil sebagai kalimat pengantar, bukan label.
            `key` membuat React memasang ulang simpulnya tiap kali kalimatnya
            berganti, jadi animasi masuknya ikut berjalan lagi saat pindah
            halaman — sementara aurora dan batik di belakangnya tidak ikut
            direset karena berada di luar simpul ini. */}
        <h1 className="hero-lead" key={subtitle}>{subtitle}</h1>
        <WaveEdge/>
      </header>
      {/* Jeda berjalan antara pita kepala dan isi halaman, sama seperti yang
          memisahkan bagian-bagian di beranda — supaya kedua jenis halaman
          memakai bahasa peralihan yang sama. */}
      <WaveDivider tone="soft"/>
      <main>{children}</main>
    </div>
    <SiteFooter/>
  </div>
}

function LoginShell({children}){
  return <div className="app login-app">
    <div className="shell">
      <Topbar active="#login"/>
      <main className="login-stage">
        <AuroraField/>
        <BatikLayer opacity={.05}/>
        {children}
      </main>
    </div>
    <SiteFooter/>
  </div>
}

/* ==========================================================================
   Beranda
   --------------------------------------------------------------------------
   Halaman ini memakai kepala halaman sendiri (bukan <Shell>) karena perannya
   berbeda: bukan judul bagian, melainkan panggung identitas — logo besar,
   nama panjang, dan kalimat pendamping — dengan foto perbatasan sebagai latar.
   ========================================================================== */

/* Foto latar bersifat opsional. Bila berkasnya belum dipasang, gradasi laut
   dan motif kawung di belakangnya sudah berdiri sendiri, jadi tidak ada
   kotak gambar rusak yang terlihat pengguna. */
const HERO_PHOTO='/hero-beranda.jpg'

/* Pemilih tahun tinggal di kepala bagian "Indikator makro", bukan di hero.
   Ia mengendalikan angka, jadi tempatnya berdampingan dengan angka pertama
   yang dipengaruhinya — bukan di panggung identitas yang tidak memuat angka
   apa pun. Bentuknya kotak bersudut lengkung, sama seperti isian lain di
   halaman ini, supaya terbaca sebagai kendali dan bukan lencana. */
function YearPicker({data,year,onYearChange}){
  const years=data?.tahun_tersedia||[]
  /* Tanpa label "Tahun data" di sebelahnya. Isinya sudah berupa tahun, dan
     kicker "Outlook 2025" tepat di seberangnya sudah menyebut tahun yang
     sedang berlaku — labelnya hanya mengulang. */
  return <label className="year-picker" aria-label="Tahun data">
    <span className="year-picker-field">
      <select
        value={year||''}
        onChange={event=>onYearChange(event.target.value)}
        disabled={!years.length}
        aria-label="Pilih tahun data yang ditampilkan"
      >
        {years.length
          ?years.map(option=><option key={option} value={option}>{option}</option>)
          :<option value="">Memuat...</option>}
      </select>
      <ChevronDown size={16} aria-hidden="true"/>
    </span>
  </label>
}

function HomeHero({data}){
  const [photo,setPhoto]=useState(true)

  return <header className="home-hero">
    <div className="home-hero-media" aria-hidden="true">
      {photo&&<img src={HERO_PHOTO} alt="" onError={()=>setPhoto(false)}/>}
    </div>
    <div className="home-hero-veil" aria-hidden="true"/>
    <AuroraField/>
    <BatikLayer opacity={.08} drift/>

    <div className="home-hero-grid">
      <div className="home-hero-identity">
        <div className="home-hero-branding">
          <h1>SEBATIK</h1>
          <p className="home-hero-expand">Sistem Monitoring Berkelanjutan Capaian Indikator ISV-IUP Kalimantan Utara</p>
        </div>
      </div>

      <div className="home-hero-copy">
        <p>
          SEBATIK memantau ketersediaan dan capaian 86 indikator ISV-IUP Provinsi Kalimantan
          Utara dalam satu dasbor terpadu. Menghubungkan target RPJPD dengan realisasi tahunan
          menuju Indonesia Emas 2045.
        </p>
      </div>
    </div>
  </header>
}

/* Empat pintu masuk utama. Angka pada kartu diambil dari muatan beranda yang
   sama, jadi tidak ada permintaan tambahan ke backend. */
const HOME_DOORS=[
  ['#indikator','Indikator',Compass,'Telusuri seri realisasi, target, dan pertumbuhan tiap indikator.'],
  ['#capaian','Capaian',Target,'Ukur jarak setiap indikator menuju target Kalimantan Utara 2045.'],
  ['#insight','Insight',Sparkles,'Baca situasi indikator makro dan perbandingan antarwilayah.'],
  ['#validitas','Validitas',ShieldCheck,'Periksa status verifikasi, pembaruan, dan metadata indikator.']
]

/* Angka ringkasan di kaki kartu dilepas. Kartu ini pintu masuk, bukan papan
   angka — dan angka yang sama sudah muncul utuh di bagian-bagian di bawahnya.
   Panah naik ke baris judul supaya kartunya tinggal dua baris: nama fitur dan
   satu kalimat penjelas. */
function HomeDoors(){
  return <Reveal as="nav" className="home-doors" aria-label="Pintu masuk utama">
    {HOME_DOORS.map(([hash,label,Icon,desc],i)=>
      <a key={hash} href={hash} className="home-door" style={{'--tone':`var(--series-${(i%6)+1})`,'--i':i}}>
        <span className="home-door-band" aria-hidden="true"/>
        <span className="home-door-icon"><Icon size={20}/></span>
        <b>{label}</b>
        <ArrowUpRight className="home-door-go" size={16} aria-hidden="true"/>
        <small>{desc}</small>
      </a>
    )}
  </Reveal>
}

/* Rel kartu mendatar yang dipakai dua tempat: korsel indikator makro di
   beranda dan pemilih indikator di halaman Insight. Keduanya memuat kartu
   selebar satu per lima layar, bergeser satu halaman penuh, dan memutar di
   ujung — yang berbeda hanya isi kartunya dan apakah ia berjalan sendiri.

   `auto` sengaja tidak dinyalakan di halaman Insight: kartu di sana adalah
   kendali yang diklik, dan kartu yang bergerak sendiri akan kabur tepat saat
   hendak ditunjuk. Di beranda kartu hanya dibaca, jadi putarannya aman.

   Rel ini tetap bisa digeser tangan; begitu kursor masuk atau ada yang
   menerima fokus papan tik, putarannya berhenti supaya tidak menarik kartu
   pergi saat sedang dibaca. */
const MACRO_INTERVAL=3000

function CardRail({count,auto=false,className='',children}){
  const railRef=useRef(null)
  /* Nomor halaman disimpan dua kali: sebagai state untuk menggambar titik
     penanda, dan sebagai ref supaya pengatur waktu membaca nilai terkini tanpa
     harus dipasang ulang tiap kali halaman berganti. */
  const pageRef=useRef(0),strideRef=useRef({stride:0,perPage:1})
  const [pages,setPages]=useState(1),[page,setPage]=useState(0),[paused,setPaused]=useState(false)

  const land=index=>{pageRef.current=index;setPage(index)}

  /* Ukuran halaman dihitung dari kartunya, bukan dari `scrollWidth` dibagi
     lebar rel. Sebabnya: satu halaman selebar rel memuat lima kartu dan empat
     sela, sedangkan melompat lima kartu berarti bergerak sejauh lima kartu dan
     lima sela — selisih satu sela tiap halaman. Pada layar lebar selisih itu
     tertelan oleh scroll-snap, tetapi di layar sempit ia menumpuk sampai
     melahirkan satu halaman hantu di deretan titik penanda. */
  const metrics=()=>{
    const rail=railRef.current
    const first=rail?.firstElementChild
    if(!rail||!rail.clientWidth||!first||!count)return null
    const gap=parseFloat(getComputedStyle(rail).columnGap)||0
    const stride=first.getBoundingClientRect().width+gap
    if(!stride)return null
    const perPage=Math.max(1,Math.round((rail.clientWidth+gap)/stride))
    return {rail,stride,perPage,total:Math.max(1,Math.ceil(count/perPage))}
  }

  const measure=()=>{
    const m=metrics()
    if(!m)return
    strideRef.current={stride:m.stride,perPage:m.perPage}
    setPages(m.total)
    /* Halaman penutup selalu mentok di ujung rel, jadi posisinya lebih pendek
       daripada kelipatan lebar halaman. Ia ditandai lewat pemeriksaan ujung,
       bukan pembagian, supaya titiknya tidak tertinggal satu langkah. */
    const atEnd=m.rail.scrollLeft+m.rail.clientWidth>=m.rail.scrollWidth-4
    land(atEnd?m.total-1:Math.min(m.total-1,Math.round(m.rail.scrollLeft/(m.perPage*m.stride))))
  }

  /* Tiap perpindahan menuju posisi mutlak halaman tujuan, bukan "geser sejauh
     satu layar dari tempat sekarang". Bedanya terasa ketika satu penggeseran
     gagal berjalan — dengan posisi mutlak, langkah berikutnya kembali ke jalur
     yang benar; dengan penambahan relatif, selisihnya menumpuk. */
  const scrollToPage=(index,behavior)=>{
    const rail=railRef.current
    const {stride,perPage}=strideRef.current
    if(!rail||!stride)return
    land(index)
    rail.scrollTo({left:index*perPage*stride,behavior})
  }

  /* Lebar rel diamati langsung, bukan lebar jendela — ia juga berubah ketika
     bilah sisi atau papan tik di layar muncul. Peristiwa `resize` tetap
     didengarkan sebagai jaring pengaman bila pengamat ukuran tidak tersedia. */
  useEffect(()=>{
    const rail=railRef.current
    if(!rail)return
    measure()
    const observer=new ResizeObserver(measure)
    observer.observe(rail)
    addEventListener('resize',measure)
    return()=>{observer.disconnect();removeEventListener('resize',measure)}
  },[count])

  useEffect(()=>{
    if(!auto||paused||pages<2)return
    const still=matchMedia('(prefers-reduced-motion: reduce)').matches
    const timer=setInterval(()=>{
      scrollToPage(pageRef.current+1>=pages?0:pageRef.current+1,still?'auto':'smooth')
    },MACRO_INTERVAL)
    return()=>clearInterval(timer)
  },[auto,paused,pages])

  const goto=index=>scrollToPage(index,'smooth')

  /* Tombol panah memutar seperti putaran otomatisnya: dari halaman terakhir
     "berikutnya" kembali ke awal, dan sebaliknya. Tidak ada tombol yang mati
     supaya kendalinya tidak pernah terasa buntu di ujung. */
  const step=arah=>goto((page+arah+pages)%pages)

  return <div
    className={`macro-rail ${className}`.trim()}
    onMouseEnter={()=>setPaused(true)}
    onMouseLeave={()=>setPaused(false)}
    onFocusCapture={()=>setPaused(true)}
    onBlurCapture={()=>setPaused(false)}
  >
    {/* Lapisan ini hanya membungkus rel kartunya, tanpa titik penanda di
        bawahnya, supaya kedua panah bisa duduk tepat di tengah tinggi kartu. */}
    <div className="macro-viewport">
      {pages>1&&<button
        type="button"
        className="macro-nav is-prev"
        onClick={()=>step(-1)}
        aria-label="Indikator sebelumnya"
      ><ChevronLeft size={20}/></button>}

      <div className="macro-track" ref={railRef} onScroll={measure}>{children}</div>

      {pages>1&&<button
        type="button"
        className="macro-nav is-next"
        onClick={()=>step(1)}
        aria-label="Indikator berikutnya"
      ><ChevronRight size={20}/></button>}
    </div>

    {pages>1&&<div className="macro-dots" role="tablist" aria-label="Halaman indikator makro">
      {Array.from({length:pages},(_,i)=>
        <button
          key={i}
          role="tab"
          className={i===page?'is-active':''}
          aria-selected={i===page}
          aria-label={`Halaman ${i+1} dari ${pages}`}
          onClick={()=>goto(i)}
        />
      )}
    </div>}
  </div>
}

function MacroCards({items,loading}){
  return <CardRail count={items.length} auto>
    {items.map((x,i)=>{
      const up=x.arah_perubahan==='NAIK',down=x.arah_perubahan==='TURUN'
      return <article className="macro-card" key={x.id_indikator} style={{'--tone':`var(--series-${(i%6)+1})`,'--i':i}}>
        <div className="macro-head"><span>{x.nama_indikator}</span><i>{x.kode_indikator}</i></div>
        <small className="macro-target">Target {x.tahun}: <b>{valueLabel(x.target,x.target_teks,x.satuan)}</b></small>
        <div className={`macro-value${valueTone(x.nilai)}`}>{valueLabel(x.nilai,x.nilai_teks,x.satuan)}</div>
        <div className="macro-change">
          <DeltaPill direction={up?'up':down?'down':'flat'}>
            {x.perubahan!==null
              ?`${valueLabel(Math.abs(x.perubahan),null,x.satuan)} dibanding tahun sebelumnya`
              :x.keterangan||'Perbandingan belum tersedia'}
          </DeltaPill>
        </div>
      </article>
    })}
    {loading&&[0,1,2,3,4].map(i=><SkeletonCard key={i}/>)}
  </CardRail>
}


const regionKey=name=>String(name||'')
  .replace(/^Kota\s+/i,'').replace(/^Kabupaten\s+/i,'').trim().toLowerCase()

function geoPaths(geo,width=560,height=390){
  const points=[]
  const collect=x=>Array.isArray(x?.[0])?x.forEach(collect):points.push(x)
  geo.features.forEach(f=>collect(f.geometry.coordinates))
  const xs=points.map(p=>p[0]),ys=points.map(p=>p[1])
  const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys),pad=18
  const scale=Math.min((width-pad*2)/(maxX-minX),(height-pad*2)/(maxY-minY))
  const offX=(width-(maxX-minX)*scale)/2,offY=(height-(maxY-minY)*scale)/2
  const project=p=>[offX+(p[0]-minX)*scale,offY+(maxY-p[1])*scale]
  const ringPath=ring=>ring.map((p,i)=>{const [x,y]=project(p);return `${i?'L':'M'}${x.toFixed(1)},${y.toFixed(1)}`}).join('')+'Z'
  return geo.features.map(f=>{
    const polys=f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates
    return {
      name:f.properties.wadmkk||f.properties.namobj,
      code:String(f.properties.kdpkab||'').replace('.',''),
      d:polys.flatMap(p=>p).map(ringPath).join('')
    }
  })
}

function KaltaraMap({regions,selected,onSelect,unit}){
  const [paths,setPaths]=useState([])
  useEffect(()=>{fetch('/kaltara-kabkota.geojson').then(r=>r.json()).then(x=>setPaths(geoPaths(x)))},[])
  const byCode=Object.fromEntries((regions||[]).map(x=>[x.kode,x]))

  return <div className="kaltara-map">
    <svg viewBox="0 0 560 390" role="img" aria-label="Peta kabupaten dan kota Kalimantan Utara">
      {paths.map(x=>{
        const item=byCode[x.code]||(regions||[]).find(r=>regionKey(r.nama)===regionKey(x.name))
        const active=selected===item?.kode
        return <path
          key={x.code||x.name}
          d={x.d}
          className={active?'active':''}
          data-status={item?.status||'BELUM_ADA_DATA'}
          tabIndex={item?0:-1}
          role={item?'button':undefined}
          aria-label={item?`${item.nama}: ${valueLabel(item.nilai,item.nilai_teks,unit)}`:undefined}
          onClick={()=>item&&onSelect(item.kode)}
          onKeyDown={e=>{if(item&&(e.key==='Enter'||e.key===' ')){e.preventDefault();onSelect(item.kode)}}}
        >
          <title>{item?.nama||x.name}: {valueLabel(item?.nilai,item?.nilai_teks,unit)}</title>
        </path>
      })}
    </svg>
    <div className="map-legend">
      <span><i className="has"/>Tersedia</span>
      <span><i/>Belum ada data</span>
    </div>
  </div>
}

export {fmt,changeNumber,displayedUnit,valueLabel,AnnualChangeTooltip,hasNumber,valueTone,growthTone,softNumber,NAV_LINKS,usePageTitle,authNavItems,CapaianBadge,MetricCard,Topbar,OFFICE_QUERY,OFFICE_EMBED,OFFICE_LINK,FOOTER_CONTACT,SiteFooter,Shell,LoginShell,HERO_PHOTO,YearPicker,HomeHero,HOME_DOORS,HomeDoors,MACRO_INTERVAL,CardRail,MacroCards,regionKey,geoPaths,KaltaraMap}
