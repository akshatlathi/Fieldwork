"use client";
import {useEffect,useState} from "react";
import Link from "next/link";
import {ShoppingBag,ArrowUpRight} from "lucide-react";
import {BottomNav} from "@/components/BottomNav";
import {Button} from "@/components/Button";
import {TopBar} from "@/components/TopBar";
import {GarmentImage} from "@/components/GarmentGallery";
import {getEscrow,getIssues,getPurchases,itemName,issueStatusText,rememberMandate,words,yen,type IssueReport,type Mandate,type Purchase} from "@/lib/api";
import s from "@/components/Flow.module.css";

type Row=Pick<Mandate,"id"|"item_id"|"amount"|"currency"|"status">&{issue_id?:string|null};
function localIds(){const ids:string[]=[];try{for(let i=0;i<localStorage.length;i++){const key=localStorage.key(i);if(key?.startsWith("fw.mandate.")){try{const v=JSON.parse(localStorage.getItem(key)??"{}");if(typeof v.id==="string")ids.push(v.id);}catch{}}}}catch{}return ids;}
export default function Purchases(){
 const [rows,setRows]=useState<Row[]>([]),[issues,setIssues]=useState<IssueReport[]>([]),[ready,setReady]=useState(false),[error,setError]=useState("");
 useEffect(()=>{let live=true;
  const load=async()=>{
   // Shared history comes from the service; purchases remembered only in this browser are merged in.
   const [shared,local,reports]=await Promise.allSettled([getPurchases(),Promise.allSettled([...new Set(localIds())].map(getEscrow)),getIssues()]);
   if(!live)return;
   const map=new Map<string,Row>();
   if(shared.status==="fulfilled")shared.value.forEach((p:Purchase)=>{map.set(p.id,p);rememberMandate(p.item_id,p);});
   if(local.status==="fulfilled")local.value.forEach(r=>{if(r.status==="fulfilled"&&!map.has(r.value.id))map.set(r.value.id,r.value);});
   setRows([...map.values()]);
   if(reports.status==="fulfilled")setIssues(reports.value);
   setError(shared.status==="rejected"||reports.status==="rejected"?"Some history could not be refreshed. Try again when the service is available.":"");
   setReady(true);};
  void load();const timer=setInterval(load,10000);return()=>{live=false;clearInterval(timer);};},[]);
 return <><TopBar title="Your purchases"/><main className={s.main}><p className="fw-section-number">THE NEXT CHAPTER</p><h1 className="t-display-m">When it arrives.</h1><p className="t-body-s t-secondary">Open a purchase to accept delivery or send evidence for a person to review. Payments in this prototype are simulated.</p>{!ready&&<p role="status">Loading purchases…</p>}{error&&<p className={s.err} role="alert">{error}</p>}{ready&&!rows.length&&<section className={s.card}><ShoppingBag/><h2 className="t-heading-s">No purchases yet</h2><p className="t-body-s">Confirmed simulated holds will appear here.</p><Link href="/agent">Find a piece <ArrowUpRight size={18}/></Link></section>}{rows.map(r=><Link key={r.id} href={"/unbox/"+encodeURIComponent(r.item_id)+"?m="+encodeURIComponent(r.id)} className={s.card}><div style={{height:180,overflow:"hidden",borderRadius:16}}><GarmentImage id={r.item_id} alt="Purchased garment" className="purchase-image"/></div><h2 className="t-heading-s">Simulated {yen(r.amount,r.currency)} · {words(r.status)}</h2><p className="t-body-s">Open the arrival check →</p></Link>)}
 <section className={s.section} aria-labelledby="issues-title"><h2 className="t-heading-s" id="issues-title">All issue reports</h2>{ready&&!issues.length&&<p className="t-body-s">No issues have been raised yet.</p>}{issues.map(report=><article className={s.card} key={report.id}><h3 className="t-heading-s">{itemName(report.listing)}</h3><p className="t-body-s">{report.buyer_text||"Received-garment issue"} · {issueStatusText(report.status)}</p><p className="t-meta">{new Date(report.updated_at).toLocaleString()} · {report.id}</p><Button variant="secondary" href={"/case/"+encodeURIComponent(report.item_id)+"?issue="+encodeURIComponent(report.id)}>Open report</Button></article>)}</section>
 </main><BottomNav/></>;
}
