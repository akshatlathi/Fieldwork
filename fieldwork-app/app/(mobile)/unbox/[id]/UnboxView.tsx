"use client";

import { useEffect, useRef, useState } from "react";
import { AIActivity } from "@/components/AIActivity";
import { BottomNav } from "@/components/BottomNav";
import { Button } from "@/components/Button";
import { CameraCapture } from "@/components/CameraCapture";
import { IssueReportView } from "@/components/IssueReportView";
import { TopBar } from "@/components/TopBar";
import { GarmentImage } from "@/components/GarmentGallery";
import { acceptDelivery, getEscrow, getIssues, getRecord, itemName, paymentStatusText, recallMandate, rememberMandate, submitIssue, yen, type ConditionRecord, type IssueReport, type Mandate } from "@/lib/api";
import { useDraftState } from "@/lib/useDraftState";
import styles from "@/components/Flow.module.css";

export function UnboxView({ id }: { id: string }) {
  const [rec, setRec] = useState<ConditionRecord | null>(null);
  const [mandate, setMandate] = useState<Mandate | null>(null);
  const [mid, setMid] = useState<string | null>(null);
  const [report, setReport] = useState<IssueReport | null>(null);
  const [mode, setMode] = useDraftState<"choose" | "issue">(`fw.unbox.${id}.mode`, "choose");
  const [text, setText] = useDraftState(`fw.unbox.${id}.text`, "");
  const [photos, setPhotos] = useDraftState<File[]>(`fw.unbox.${id}.photos`, [], false);
  const [busy, setBusy] = useDraftState(`fw.unbox.${id}.busy`, false, false);
  const [ready, setReady] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useDraftState(`fw.unbox.${id}.error`, "");
  const confirmation = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    let live = true;
    const known = new URLSearchParams(window.location.search).get("m") ?? recallMandate(id)?.id ?? null;
    setMid(known);
    Promise.all([getRecord(id), getIssues(id), known ? getEscrow(known) : Promise.resolve(null)]).then(([r, issues, m]) => {
      if (!live) return;
      if (m && m.item_id !== id) throw new Error("This escrow belongs to another garment. Open the correct purchase.");
      setRec(r); setReport((known ? issues.find(issue => issue.mandate_id === known) : issues[0]) ?? null); setMandate(m); setReady(true);
    }).catch((e: Error) => { if (live) setError(e.message); });
    return () => { live = false; };
  }, [id]);

  useEffect(() => {
    if (!report?.id) return;
    let live = true;
    const timer = setInterval(async () => {
      try {
        const [issues, current] = await Promise.all([getIssues(id), mid ? getEscrow(mid) : Promise.resolve(null)]);
        if (live) { setReport(issues.find(issue => issue.id === report.id) ?? report); if (current) setMandate(current); }
      } catch { /* Keep the saved report visible while the service reconnects. */ }
    }, 10000);
    return () => { live = false; clearInterval(timer); };
  }, [id, mid, report?.id]);

  async function allGood() {
    setBusy(true); setError("");
    try {
      if (mid) { const m = await acceptDelivery(mid); setMandate(m); rememberMandate(id, m); }
      setAccepted(true);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not confirm acceptance."); }
    finally { setBusy(false); }
  }

  async function submit(clip: Blob | null) {
    setBusy(true); setError("");
    try {
      const r = await submitIssue(id, text.trim(), mid, clip, photos.length ? photos : undefined);
      setReport(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not submit your issue.");
      // Recover a queued report if the request completed but its response was lost.
      try { const reports = await getIssues(id); const queued = mid ? reports.find(r => r.mandate_id === mid) : reports[0]; if (queued) setReport(queued); } catch {}
    } finally { setBusy(false); }
  }

  return <>
    <TopBar title="Received garment" backHref={`/pass/${id}`} titleAs="p" />
    <main className={styles.main}>
      <p className="fw-section-number">THE SECOND MOMENT</p>
      <div className="fw-arrival-image"><GarmentImage id={id} alt="Original listing garment"/></div>
      <section className={styles.section}>
        <h1 className="t-heading-m">{rec ? itemName(rec) : "Your garment"}</h1>
        {mandate && <p className="t-body-s">Simulated payment {yen(mandate.amount, mandate.currency)} · {paymentStatusText(mandate.status)}</p>}
      </section>
      {error && <p className={styles.err} role="alert">{error}</p>}
      {busy && <AIActivity title={mode === "issue" ? "Preparing evidence for a human reviewer…" : "Recording your acceptance…"} variant="plain" />}
      {!ready && !error && <p className="t-body-s">Loading your purchase…</p>}
      {accepted ? <section className={styles.card} role="status">
        <h2 className="t-heading-s">You accepted the garment</h2>
        <p className="t-body">{mandate ? "Simulated: the seller has been paid. No real money moved." : "Your acceptance is confirmed on this device. No escrow was attached."}</p>
      </section> : report ? <>
        <IssueReportView report={report} />
        <Button href={`/case/${id}?issue=${report.id}`} fullWidth>Open your report</Button>
      </> : ready && !busy && (mandate && mandate.status !== "held" ? <p className="t-body">This purchase has already been settled.</p> : mode === "choose" ? <section className={styles.section}>
        <p className="t-body">Check the garment. Accept it if everything is good, or raise an issue for a person to review.</p>
        <Button fullWidth disabled={!mandate} onClick={()=>confirmation.current?.showModal()}>All good</Button>
        {!mandate && <p className="t-body-s">No purchase is attached. <a href={`/pass/${id}`}>Open the listing to purchase</a>. You can still submit evidence for a demo review.</p>}
        <Button fullWidth variant="secondary" onClick={() => setMode("issue")}>Raise an issue</Button>
      </section> : <section className={styles.section}>
        <h2 className="t-heading-s">What went wrong?</h2>
        <label htmlFor="buyer-issue" className="t-label">Describe the issue (optional)</label>
        <textarea id="buyer-issue" rows={3} maxLength={5000} className={styles.field} value={text} onChange={e => setText(e.target.value)} placeholder="There is a stain on the left cuff that was not shown in the listing." />
        <p className="t-body-s">Record the front, back, collar, cuffs, hem and the area you are concerned about. Your evidence and the inspection suggestion go to a human.{mandate ? " The simulated payment stays on hold until a person decides." : " No escrow is attached to this demo review."}</p>
        <CameraCapture seconds={12} recordLabel="Record received garment" idleText="Hold the camera steady with good light." onRecorded={clip => submit(clip)} />
        <label htmlFor="received-photos" className="t-label">Or upload received-garment photos</label>
        <input id="received-photos" className={styles.field} type="file" accept="image/*" multiple onChange={e => setPhotos(Array.from(e.target.files ?? []))} />
        {photos.length > 0 && <p className="t-body-s">Selected photos: {photos.map(file => file.name).join(", ")}</p>}
        <Button fullWidth disabled={!photos.length} onClick={() => submit(null)}>Submit photos for human review</Button>
        <Button variant="tertiary" onClick={() => setMode("choose")}>Back</Button>
      </section>)}
    </main>
    <dialog ref={confirmation} className="fw-confirm-dialog"><h2 className="t-heading-m">Accept this delivery?</h2><p className="t-body-s">{mid?"This pays the seller (simulated). If you have a concern, raise an issue instead.":"This records acceptance on this device. No simulated hold is attached."}</p><Button fullWidth loading={busy} onClick={async()=>{await allGood();confirmation.current?.close();}}>Confirm acceptance</Button><Button fullWidth variant="secondary" disabled={busy} onClick={()=>confirmation.current?.close()}>Keep checking</Button></dialog>
    <BottomNav />
  </>;
}
