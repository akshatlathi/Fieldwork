"use client";
import {useEffect,useRef,useState} from "react";
import {Expand,ImageOff,X} from "lucide-react";
import {frameUrl,getRecord,type Box,type ConditionRecord} from "@/lib/api";
import styles from "./GarmentGallery.module.css";

export function GarmentImage({id,alt,className}:{id:string;alt:string;className?:string}){
  const [src,setSrc]=useState(""); const [failed,setFailed]=useState(false);
  useEffect(()=>{let live=true;setSrc("");setFailed(false);getRecord(id).then(r=>{if(live&&r.capture.frames[0])setSrc(frameUrl(id,r.capture.frames[0]));}).catch(()=>{});return()=>{live=false;};},[id]);
  return src&&!failed?<img className={className} src={src} alt={alt} loading="lazy" onError={()=>setFailed(true)}/>:<div className={styles.missing}><ImageOff size={24}/><span>Image unavailable</span></div>;
}
export function GarmentGallery({record,selected,onSelect,compact=false}:{record:ConditionRecord;selected?:Box|null;onSelect?:(b:Box|null)=>void;compact?:boolean}){
  const frames=record.capture.frames;const [frame,setFrame]=useState(frames[0]??"");const [failed,setFailed]=useState(false);const dialog=useRef<HTMLDialogElement>(null);
  useEffect(()=>{if(selected&&frames.includes(selected.frame_id)){setFrame(selected.frame_id);setFailed(false);}},[selected,frames]);
  const box=selected?.frame_id===frame?selected.box_2d:null;
  const valid=box&&box.every(n=>Number.isFinite(n)&&n>=0&&n<=1000)&&box[2]>box[0]&&box[3]>box[1];
  return <section className={`${styles.gallery} ${compact?styles.compact:""}`} aria-label="Garment source images">
    <div className={styles.stage}>
      <span className={styles.tag}>GARMENT PASS / {record.id.replace(/^fx_/,"").slice(0,20)}</span>
      {frame&&!failed?<div className={styles.imageWrap}><img src={frameUrl(record.id,frame)} alt={`Original garment evidence, ${frame}`} onError={()=>setFailed(true)}/>{valid&&<span className={styles.box} style={{top:`${box![0]/10}%`,left:`${box![1]/10}%`,height:`${(box![2]-box![0])/10}%`,width:`${(box![3]-box![1])/10}%`}}><span>Selected evidence</span></span>}</div>:<div className={styles.missing}><ImageOff/><p>No source image available</p></div>}
      <button className={styles.expand} aria-label="Open full source image" disabled={!frame||failed} onClick={()=>dialog.current?.showModal()}><Expand size={18}/></button>
    </div>
    {frames.length>1&&<div className={styles.strip} aria-label="Choose a captured frame">{frames.map((f,i)=><button key={f} aria-label={`View source ${i+1}: ${f}`} aria-pressed={frame===f} onClick={()=>{setFrame(f);setFailed(false);onSelect?.(null);}}><img src={frameUrl(record.id,f)} alt="" loading="lazy"/><span>{String(i+1).padStart(2,"0")}</span></button>)}</div>}
    <p className="fw-disclosure">{frame?`Source ${frame} · Original capture` : "Capture evidence to see it here"}{valid?" · Region highlighted in its source frame":""}</p>
    <dialog ref={dialog} className={styles.dialog}><div className={styles.dialogHeader}><p>Original source · {frame}</p><button aria-label="Close source image" onClick={()=>dialog.current?.close()}><X/></button></div>{frame&&<img src={frameUrl(record.id,frame)} alt={`Full original garment source ${frame}`}/>}<p className="fw-disclosure">Source image shown without colour filters. Pinch to zoom on your device.</p></dialog>
  </section>;
}
