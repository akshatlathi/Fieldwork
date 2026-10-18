"use client";

import { useEffect, useState } from "react";
import { AIActivity } from "@/components/AIActivity";
import { BottomNav } from "@/components/BottomNav";
import { Button } from "@/components/Button";
import { CameraCapture } from "@/components/CameraCapture";
import { IssueReportView } from "@/components/IssueReportView";
import { TopBar } from "@/components/TopBar";
import { addIssueEvidence, getIssues, type IssueReport } from "@/lib/api";
import { useDraftState } from "@/lib/useDraftState";
import styles from "@/components/Flow.module.css";

export function CaseView({ id }: { id: string }) {
  const [report, setReport] = useState<IssueReport | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [photos, setPhotos] = useDraftState<File[]>(`fw.case.${id}.photos`, [], false);
  const [busy, setBusy] = useDraftState(`fw.case.${id}.busy`, false, false);
  const [error, setError] = useDraftState(`fw.case.${id}.error`, "");

  useEffect(() => {
    let live = true;
    const refresh = async () => {
      try {
        const reports = await getIssues(id);
        const selected = new URLSearchParams(window.location.search).get("issue");
        if (live) { setReport((selected ? reports.find(r => r.id === selected) : reports[0]) ?? null); setLoaded(true); }
      } catch (e) { if (live) setError(e instanceof Error ? e.message : "Could not load report."); }
    };
    refresh(); const timer = setInterval(refresh, 10000);
    return () => { live = false; clearInterval(timer); };
  }, [id]);

  async function submit(clip: Blob | null) {
    if (!report) return;
    setBusy(true); setError("");
    try { setReport(await addIssueEvidence(report.id, clip, photos.length ? photos : undefined)); setPhotos([]); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not add evidence."); }
    finally { setBusy(false); }
  }

  return <>
    <TopBar title="Human review report" backHref={`/unbox/${id}`} titleAs="p" />
    <main className={styles.main}>
      {error && <p className={styles.err} role="alert">{error}</p>}
      {!loaded && !error && <p className="t-body">Loading your report…</p>}
      {loaded && !report && <section className={styles.card}>
        <h1 className="t-heading-s">No issue report yet</h1>
        <p className="t-body">Raise an issue and capture the received garment to send evidence for human review.</p>
        <Button href={`/unbox/${id}`}>Check received garment</Button>
      </section>}
      {report && <IssueReportView report={report} />}
      <Button variant="secondary" href="/help">All issue reports</Button>
      {busy && <AIActivity title="Adding evidence to your report…" variant="plain" />}
      {report?.status === "needs_evidence" && !busy && <section className={styles.section}>
        <h2 className="t-heading-s">Add the requested evidence</h2>
        <CameraCapture seconds={8} recordLabel="Record a close-up" idleText="Follow the reviewer's request above." onRecorded={clip => submit(clip)} />
        <label className="t-label" htmlFor="more-photos">Or upload photos</label>
        <input id="more-photos" className={styles.field} type="file" accept="image/*" multiple onChange={e => setPhotos(Array.from(e.target.files ?? []))} />
        {photos.length > 0 && <p className="t-body-s">Selected photos: {photos.map(file => file.name).join(", ")}</p>}
        <Button disabled={!photos.length} onClick={() => submit(null)}>Send additional photos</Button>
      </section>}
    </main>
    <BottomNav />
  </>;
}
