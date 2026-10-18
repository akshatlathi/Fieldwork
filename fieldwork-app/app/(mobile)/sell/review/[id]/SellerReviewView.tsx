"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { TopBar } from "@/components/TopBar";
import { BottomNav } from "@/components/BottomNav";
import { Button } from "@/components/Button";
import { Crop } from "@/components/Crop";
import { AIActivity } from "@/components/AIActivity";
import { GarmentGallery } from "@/components/GarmentGallery";
import { addSellerEvidence, evidenceUrl, getSellerDraft, itemName, publishSellerDraft, saveSellerDeclarations,
  saveSellerPrice, sentence, yen, words, type SellerDraft, type SellerIssue } from "@/lib/api";
import { readDraftState, useDraftState } from "@/lib/useDraftState";
import styles from "@/components/Flow.module.css";

const CODES = ["stain", "hole", "tear", "pilling", "fading", "snag", "loose_seam", "missing_button", "broken_zip", "discolour", "other"];
const REGIONS = ["whole", "front", "back", "collar", "left_sleeve", "right_sleeve", "left_cuff", "right_cuff", "left_armpit", "right_armpit", "hem", "pocket", "waistband", "zip", "label"];

export function SellerReviewView({ id }: { id: string }) {
  const router = useRouter();
  const mounted = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const [draft, setDraft] = useDraftState<SellerDraft | null>(`fw.seller.${id}.draft`, null);
  const [answer, setAnswer] = useDraftState<NonNullable<SellerDraft["answer"]> | "">(`fw.seller.${id}.answer`, "");
  const [issues, setIssues] = useDraftState<SellerIssue[]>(`fw.seller.${id}.issues`, []);
  const [photos, setPhotos] = useDraftState<File[]>(`fw.seller.${id}.photos`, [], false);
  const [video, setVideo] = useDraftState<File | null>(`fw.seller.${id}.video`, null, false);
  const [ack, setAck] = useDraftState(`fw.seller.${id}.ack`, false, false);
  const [busy, setBusy] = useDraftState(`fw.seller.${id}.busy`, "", false);
  const [error, setError] = useDraftState(`fw.seller.${id}.error`, "");
  const [stage, setStage] = useState(0);
  const [askingPrice, setAskingPrice] = useDraftState(`fw.seller.${id}.askingPrice`, "");
  const [negotiation, setNegotiation] = useDraftState(`fw.seller.${id}.negotiation`, false);
  const [minimum, setMinimum] = useDraftState(`fw.seller.${id}.minimum`, "", false);
  function adopt(next: SellerDraft) { setDraft(next); setAnswer(next.answer ?? ""); setIssues(next.issues); setAck(false);
    setAskingPrice(next.asking_price ? String(next.asking_price) : ""); setNegotiation(!!next.negotiation_enabled); setMinimum(""); }
  useEffect(() => { getSellerDraft(id).then(next => {
    const previous = readDraftState<SellerDraft | null>(`fw.seller.${id}.draft`, null);
    if (!previous) adopt(next);
    else {
      setDraft(next); // preserve unsaved fields when returning to this route
      if (previous.revision !== next.revision) { setAck(false); setError("The saved listing changed while you were away. Review your retained edits before saving."); }
    }
  }).catch(e => setError(e.message)); }, [id]);
  async function action(label: string, fn: () => Promise<SellerDraft>) {
    setBusy(label); setError("");
    try { const next = await fn(); adopt(next); return next; }
    catch (e) { setError(e instanceof Error ? e.message : "Could not save this change."); }
    finally { setBusy(""); }
  }
  if (!draft) return <><TopBar title="Review draft" /><main className={styles.main}>
    {error ? <p className={styles.err} role="alert">{error}</p> : <AIActivity title="Loading seller draft…" />}
  </main></>;
  const dirty = answer !== (draft.answer ?? "") || JSON.stringify(issues) !== JSON.stringify(draft.issues);
  const published = draft.status === "published";
  const valid = answer !== "" && (answer !== "issues_reported" || (issues.length > 0 && issues.every(i => i.description.trim())));
  const locked = !!busy || published;
  const priceDirty = Number(askingPrice) !== (draft.asking_price ?? 0) || negotiation !== !!draft.negotiation_enabled || minimum !== "";
  const priceValid = Number.isInteger(Number(askingPrice)) && Number(askingPrice) > 0 && Number(askingPrice) <= 10000000 &&
    (!negotiation || (Number.isInteger(Number(minimum)) && Number(minimum) > 0 && Number(minimum) <= Number(askingPrice)));
  function edit(index: number, key: keyof SellerIssue, value: string) {
    setIssues(current => current.map((issue, i) => i === index ? { ...issue, [key]: value } : issue));
  }
  return <>
    <TopBar title="Review seller draft" backHref="/sell" />
    <main className={styles.main}>
      <div className="fw-stage-nav" role="group" aria-label="Review stages">{["Review evidence", "Disclose & add", "Publish"].map((label,i)=><button key={label} aria-pressed={stage===i} onClick={()=>setStage(i)}><span>{String(i+1).padStart(2,"0")}</span>{label}</button>)}</div>
      <section className={styles.section}>
        <p className="t-overline">{published ? "Published" : "Draft · not available to buyers"}</p>
        <h1 className="t-heading-l">{itemName(draft.record)}</h1>
        <p className="t-body-s t-secondary">Review the observations, disclose known issues and add evidence before publishing. Folds and overview photos can hide defects.</p>
      </section>
      {error && <p role="alert" className={styles.err}>{error}</p>}
      {busy && <p role="status" className="t-body-s">{busy}</p>}
      <p className="fw-disclosure" role="status">{published?"Published record":dirty?"Unsaved condition changes · save before adding evidence or publishing":"Current changes saved"}</p>
      {stage===0&&<GarmentGallery record={draft.record}/>}
      <section className={styles.card} hidden={stage!==0}>
        <h2 className="t-heading-s">What the images show</h2>
        <p className="t-body-s t-secondary">These observations are limited to the supplied views. Your disclosures remain separate.</p>
        {draft.record.claims.filter(c => c.lane !== "declared").map(c => <div className={styles.item} key={c.id}>
          <p className="t-body-s">{words(c.lane)} · {words(c.region)} · {c.note || words(c.code)}</p>
          <div className={styles.thumbs}>{c.evidence.slice(0, 2).map((box, i) => <Crop key={i} itemId={id} box={box} label={box.frame_id} />)}</div>
        </div>)}
      </section>
      <section className={styles.card} hidden={stage!==1}>
        <h2 className="t-heading-s">What do you know about its condition?</h2>
        <label className="t-label" htmlFor="seller-answer">Known issues</label>
        <select id="seller-answer" className={styles.field} disabled={locked} value={answer} onChange={e => {
          const value = e.target.value as typeof answer; setAnswer(value);
          if (value !== "issues_reported") setIssues([]);
          else if (!issues.length) setIssues([{ code: "hole", region: "whole", description: "" }]);
        }}>
          <option value="">Choose an answer</option><option value="issues_reported">I know of issues</option>
          <option value="none_known">I know of no issues</option><option value="unknown">I am not sure</option>
        </select>
        <p className="t-body-s t-secondary">Your answer is seller-declared, not visually confirmed. Include issues hidden by folds.</p>
        {issues.map((issue, index) => <div key={index} className={styles.card}>
          <label className="t-label" htmlFor={`issue-code-${index}`}>Issue type</label>
          <select id={`issue-code-${index}`} className={styles.field} value={issue.code} disabled={locked} onChange={e => edit(index, "code", e.target.value)}>{CODES.map(c => <option value={c} key={c}>{words(c)}</option>)}</select>
          <label className="t-label" htmlFor={`issue-region-${index}`}>Area</label>
          <select id={`issue-region-${index}`} className={styles.field} value={issue.region} disabled={locked} onChange={e => edit(index, "region", e.target.value)}>{REGIONS.map(r => <option value={r} key={r}>{r === "whole" ? "Location unclear / whole garment" : words(r)}</option>)}</select>
          <label className="t-label" htmlFor={`issue-description-${index}`}>Location and description</label>
          <textarea id={`issue-description-${index}`} className={styles.field} rows={3} maxLength={500} disabled={locked} value={issue.description} placeholder="For example: small hole behind the left pocket, hidden by a fold" onChange={e => edit(index, "description", e.target.value)} />
          <Button variant="tertiary" disabled={locked} onClick={() => setIssues(current => current.filter((_, i) => i !== index))}>Remove issue</Button>
        </div>)}
        {answer === "issues_reported" && <Button variant="secondary" disabled={locked || issues.length >= 20} onClick={() => setIssues(current => [...current, { code: "other", region: "whole", description: "" }])}>Add another issue</Button>}
        <Button disabled={locked || !valid || !dirty} onClick={() => action("Saving seller disclosures…", () => saveSellerDeclarations(id, draft.revision, answer as NonNullable<SellerDraft["answer"]>, issues))}>Save condition answer</Button>
      </section>
      <section className={styles.card} hidden={stage!==1}>
        <h2 className="t-heading-s">Additional evidence to capture</h2>
        <ul>{draft.guidance.map((text, i) => <li className="t-body-s" key={i}>{text}</li>)}</ul>
        <label className="t-label" htmlFor="seller-closeups">Close-up and context photos</label>
        <input id="seller-closeups" type="file" className={styles.field} accept="image/*" multiple disabled={locked} onChange={e => setPhotos(Array.from(e.target.files ?? []))} />
        <label className="t-label" htmlFor="seller-retake">Optional new video</label>
        <input id="seller-retake" type="file" className={styles.field} accept="video/*" disabled={locked} onChange={e => setVideo(e.target.files?.[0] ?? null)} />
        {(photos.length > 0 || video) && <p className="t-body-s">Selected evidence: {[...photos.map(file => file.name), ...(video ? [video.name] : [])].join(", ")}</p>}
        <p className="t-body-s t-secondary">Unfold the relevant area. Include a close-up and a wider view with a nearby seam or pocket. Earlier evidence is preserved. Save any changed disclosures first.</p>
        <Button variant="secondary" disabled={locked || dirty || (!photos.length && !video)} onClick={async () => {
          const next = await action("Inspecting additional evidence…", () => addSellerEvidence(id, draft.revision, photos, video));
          if (next) { setPhotos([]); setVideo(null); }
        }}>Add evidence and reinspect</Button>
      </section>
      <section className={styles.card} hidden={stage!==2}>
        <h2 className="t-heading-s">Your asking price</h2>
        <p className="t-body-s t-secondary">Set the price in INR. No automatic estimate or currency conversion is used. Condition grades describe the garment only.</p>
        <label className="t-label" htmlFor="asking-price">Asking price (INR)</label>
        <input id="asking-price" className={styles.field} type="number" min={1} max={10000000} step={1} inputMode="numeric" value={askingPrice} disabled={!!busy || (published && !!draft.asking_price)} onChange={e => setAskingPrice(e.target.value)} />
        <label className="t-body-s"><input type="checkbox" checked={negotiation} disabled={!!busy || (published && !!draft.asking_price)} onChange={e => setNegotiation(e.target.checked)} /> Allow negotiation</label>
        {negotiation && <><label className="t-label" htmlFor="minimum-price">Private minimum acceptable price (INR)</label>
          <input id="minimum-price" className={styles.field} type="number" min={1} max={Number(askingPrice) || undefined} step={1} value={minimum} disabled={!!busy || (published && !!draft.asking_price)} onChange={e => setMinimum(e.target.value)} placeholder={draft.asking_price ? "Saved privately; enter again to change pricing" : "Only the backend uses this minimum"} />
          <p className="t-caption t-secondary">Buyers and agents never receive this minimum. Up to five rounds; each quote is valid for 30 minutes.</p></>}
        {draft.asking_price && <p className="t-body-s">Saved asking price: {yen(draft.asking_price, "INR")}.</p>}
        <Button disabled={!!busy || (published && !!draft.asking_price) || dirty || !priceDirty || !priceValid} onClick={() => action("Saving seller price…", () => saveSellerPrice(id, draft.revision, Number(askingPrice), negotiation, negotiation ? Number(minimum) : undefined))}>Save asking price</Button>
      </section>
      <section className={styles.card} hidden={stage!==2}>
        <h2 className="t-heading-s">Limitations buyers will see</h2>
        <ul className={styles.bullets}>{draft.limitations.map((text, i) => <li key={i} className="t-body-s">{sentence(text)}</li>)}</ul>
        <p className="t-body-s">{draft.record.listing_text_en}</p>
        {!published && <>
          <label className="t-body-s"><input type="checkbox" checked={ack} disabled={locked || dirty} onChange={e => setAck(e.target.checked)} /> I reviewed this draft and understand that seller-reported issues and unresolved limitations will remain visible to buyers.</label>
          <Button fullWidth disabled={locked || dirty || priceDirty || !draft.asking_price || !draft.answer || !ack} onClick={async () => {
            const next = await action("Publishing the reviewed listing…", () => publishSellerDraft(id, draft.revision, ack));
            if (next && mounted.current) router.push(`/pass/${id}`);
          }}>Approve and publish with these limitations</Button>
        </>}
        {published && <Button href={`/pass/${id}`}>Open published Pass</Button>}
      </section>
      {stage<2&&<Button fullWidth disabled={stage===1&&(dirty||!draft.answer)} onClick={()=>setStage(stage+1)}>{stage===0?"Continue to disclosures":"Preview publication"}</Button>}
      {stage>0&&<Button variant="tertiary" onClick={()=>setStage(stage-1)}>Previous step</Button>}
      <section className={styles.card} hidden={stage!==2}>
        <h2 className="t-heading-s">Capture history</h2>
        {draft.attempts.map(attempt => <div className={styles.item} key={attempt.id}>
          <p className="t-body-s">{new Date(attempt.created_at).toLocaleString()} · {words(attempt.status)}</p>
          {attempt.error && <p role="status" className="t-body-s">{attempt.error}</p>}
          <div className={styles.row}>{attempt.media.map((media, i) => <a className="t-body-s" key={media.url} href={evidenceUrl(media.url)} target="_blank" rel="noreferrer">Original capture {i + 1}</a>)}</div>
        </div>)}
      </section>
    </main><BottomNav />
  </>;
}
