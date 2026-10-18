"use client";
import {useEffect,useState} from "react";
import Link from "next/link";
import {ArrowUpRight,Search,SlidersHorizontal,Heart,Sparkles,RotateCcw,Scale} from "lucide-react";
import {BottomNav} from "@/components/BottomNav";
import {TopBar} from "@/components/TopBar";
import {GarmentImage} from "@/components/GarmentGallery";
import {searchGarments,yen,itemName,type SearchCard} from "@/lib/api";
import {useBought} from "@/lib/useBought";
import s from "./home.module.css";
export default function HomePage(){
 const [items,setItems]=useState<SearchCard[]>([]),[error,setError]=useState(""),[loading,setLoading]=useState(true),[query,setQuery]=useState("");
 async function load(){setLoading(true);setError("");try{setItems(await searchGarments());}catch(e){setError(e instanceof Error?e.message:"Could not load listings.");}finally{setLoading(false);}}
 useEffect(()=>{void load();},[]);
 const shown=items.filter(i=>(itemName(i)+" "+i.item.material).toLowerCase().includes(query.toLowerCase()));
 return <><TopBar variant="brand" trailing={<Link className={s.round} href="/purchases" aria-label="Your purchases"><Heart size={20}/></Link>}/>
 <main className={s.main}>
 <div className={s.heading}><div><h1>Discover</h1><p>Pieces with a story.</p></div></div>
 <label className={s.search}><Search size={20}/><span className="sr-only">Search available garments</span><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Find a piece"/><Link href="/agent" aria-label="Search with your agent"><SlidersHorizontal size={19}/></Link></label>
 {loading?<div className={s.loading} role="status">Finding available pieces…</div>:shown.length?<section aria-label="Available garments" className={s.products}>{shown.map((item,i)=><Link key={item.id} href={"/pass/"+encodeURIComponent(item.id)} className={i===0?s.feature:s.product}><div className={s.photo}><GarmentImage id={item.id} alt={itemName(item)}/><span className={s.photoTag}>{item.cant_judge.length?"Some views unknown":"Open the evidence"}</span><BoughtBadge id={item.id}/></div><div className={s.productInfo}><div><h2>{itemName(item)||"Garment"}</h2><p>{item.purchase_price?yen(item.purchase_price,item.currency||"INR"):"Seller price not set"}</p></div><span className={s.arrow}><ArrowUpRight size={20}/></span></div></Link>)}</section>:<section className={s.example}><div className={s.examplePhoto}><img src="/illustrations/leather-bomber.png" alt="Illustrative cognac leather bomber, not a live listing"/></div><div className={s.exampleInfo}><div><h2>A closer look at Fieldwork</h2><p>Explore the designed experience</p></div><Link href="/design" className={s.arrow} aria-label="Explore the illustrative product demo"><ArrowUpRight size={20}/></Link></div><p className="fw-disclosure">Illustration · generated with OpenAI · example, not a live listing</p></section>}
 {error&&<div className={s.service} role="status"><p>Live listings are unavailable.</p><p className="fw-disclosure">{error}</p><button onClick={load}><RotateCcw size={14}/>Try again</button></div>}
 {!loading&&!error&&!shown.length&&<p className="fw-disclosure">{items.length?"No pieces match this search. Try a broader description.":"No published pieces yet. Capture a garment to start."}</p>}
 <Link href="/agent" className={s.agent}><Sparkles size={19}/><div><strong>Looking for something specific?</strong><span>Tell your agent what matters.</span></div><ArrowUpRight size={20}/></Link>
 <Link href="/help" className={s.agent}><Scale size={19}/><div><strong>Help and issue history</strong><span>See where your issues stand and what was decided.</span></div><ArrowUpRight size={20}/></Link>
  <div className={s.editorial}><span>01 / THE FIELDWORK WAY</span><h2>Look closer.<br/>Decide with context.</h2><p>What is shown, what the seller says, and what a photo cannot tell you—kept distinct.</p><Link href="/sell">Create a Garment Pass <ArrowUpRight size={16}/></Link></div>
 </main><BottomNav/></>;
}

function BoughtBadge({id}:{id:string}){const b=useBought(id);return b?<span className={s.photoTag} style={{left:"auto",right:10,top:10,bottom:"auto"}}>You bought this</span>:null;}
