import {lazy,Suspense,useEffect,useState} from 'react'
import {ChartSkeleton} from './ui'

const HomePage=lazy(()=>import('./routes/HomePage'))
const IndicatorExplorerPage=lazy(()=>import('./routes/IndicatorExplorerPage'))
const CapaianPage=lazy(()=>import('./routes/CapaianPage'))
const DetailPage=lazy(()=>import('./routes/DetailPage'))
const InsightPage=lazy(()=>import('./routes/InsightPage'))
const ValidityPage=lazy(()=>import('./routes/ValidityPage'))
const AnalyticsPage=lazy(()=>import('./routes/AnalyticsPage'))
const AdminPage=lazy(()=>import('./routes/AdminPage'))

function RouteFallback(){
  return <main className="route-fallback"><ChartSkeleton/></main>
}

export default function App(){
  const [hash,setHash]=useState(location.hash||'#beranda')
  useEffect(()=>{
    const onHashChange=()=>{setHash(location.hash||'#beranda');scrollTo({top:0})}
    addEventListener('hashchange',onHashChange)
    return()=>removeEventListener('hashchange',onHashChange)
  },[])

  let page
  if(hash.startsWith('#detail/'))page=<DetailPage id={hash.split('/')[1]}/>
  else if(hash==='#indikator')page=<IndicatorExplorerPage/>
  else if(hash==='#capaian')page=<CapaianPage/>
  else if(hash==='#insight')page=<InsightPage/>
  else if(hash==='#validitas')page=<ValidityPage/>
  else if(hash==='#analitik')page=<AnalyticsPage/>
  else if(hash==='#admin'||hash==='#login')page=<AdminPage/>
  else page=<HomePage/>

  return <Suspense fallback={<RouteFallback/>}>{page}</Suspense>
}
