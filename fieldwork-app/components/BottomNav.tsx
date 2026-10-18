"use client";
import Link from "next/link";
import {usePathname} from "next/navigation";
import {useEffect} from "react";
import {useDraftState} from "@/lib/useDraftState";
import {Camera,Compass,ShoppingBag,Sparkles} from "lucide-react";
import styles from "./BottomNav.module.css";
const items=[
{id:"home",label:"Discover",href:"/",Icon:Compass,match:(p:string)=>p==="/",camera:false},
{id:"agent",label:"Agent",href:"/agent",Icon:Sparkles,match:(p:string)=>p.startsWith("/agent")||p.startsWith("/pass"),camera:false},
{id:"sell",label:"Capture",href:"/sell",Icon:Camera,match:(p:string)=>p.startsWith("/sell"),camera:true},
{id:"purchases",label:"Purchases",href:"/purchases",Icon:ShoppingBag,match:(p:string)=>p.startsWith("/purchases")||p.startsWith("/unbox")||p.startsWith("/case")||p==="/help",camera:false}];
const RE:Record<string,RegExp>={agent:/^\/(agent|pass\/)/,sell:/^\/sell/,purchases:/^\/(purchases|unbox\/|case\/|help)/};
export function BottomNav(){const path=usePathname()??"/";
const [agentRoute,setAgentRoute]=useDraftState("fw.nav.buyer","/agent");const [sellRoute,setSellRoute]=useDraftState("fw.nav.seller","/sell");
useEffect(()=>{const r=path+window.location.search;if(RE.agent.test(path))setAgentRoute(r);if(RE.sell.test(path))setSellRoute(r);},[path,setAgentRoute,setSellRoute]);
const saved:Record<string,string>={agent:agentRoute,sell:sellRoute};
const hrefFor=(it:typeof items[number])=>{const s=saved[it.id];return s&&RE[it.id]?.test(s)?s:it.href;};
return <nav className={styles.nav} aria-label="Main navigation"><ul className={styles.list}>{items.map(it=><li key={it.href}><Link href={hrefFor(it)} className={styles.link+" "+(it.match(path)?styles.active:"")+" "+(it.camera?styles.capture:"")} aria-current={it.match(path)?"page":undefined}><span className={styles.icon}><it.Icon size={22} strokeWidth={1.6} aria-hidden="true"/></span><span>{it.label}</span></Link></li>)}</ul></nav>;}
