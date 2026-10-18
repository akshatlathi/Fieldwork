"use client";

import { useDraftState } from "@/lib/useDraftState";
import { Button } from "@/components/Button";
import { IssueReportView, assessmentLabel } from "@/components/IssueReportView";
import { Wordmark } from "@/components/Logo";
import { decideIssue, itemName, reviewQueue, words, type HumanDecision, type IssueReport } from "@/lib/api";
import flow from "@/components/Flow.module.css";
import styles from "./review.module.css";

export default function ReviewPage() {
  const [token, setToken] = useDraftState("fw.reviewer.token", "", false);
  const [reports, setReports] = useDraftState<IssueReport[]>("fw.reviewer.reports", [], false);
  const [selected, setSelected] = useDraftState("fw.reviewer.selected", "", false);
  const [loaded, setLoaded] = useDraftState("fw.reviewer.loaded", false, false);
  const [busy, setBusy] = useDraftState("fw.reviewer.busy", false, false);
  const [error, setError] = useDraftState("fw.reviewer.error", "", false);
  const [choice, setChoice] = useDraftState<HumanDecision["action"] | "">("fw.reviewer.choice", "", false);
  const [pct, setPct] = useDraftState("fw.reviewer.pct", 0, false);
  const [name, setName] = useDraftState("fw.reviewer.name", "", false);
  const [note, setNote] = useDraftState("fw.reviewer.note", "", false);
  const report = reports.find(r => r.id === selected);

  function select(id: string) { setSelected(id); setChoice(""); setPct(0); setNote(""); }

  async function load() {
    setBusy(true); setError("");
    try {
      const rows = await reviewQueue(token);
      setReports(rows); setLoaded(true);
      if (!rows.some(r => r.id === selected)) select(rows[0]?.id ?? "");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load review queue."); }
    finally { setBusy(false); }
  }

  async function decide() {
    if (!report || !choice) return;
    setBusy(true); setError("");
    try {
      const updated = await decideIssue(report.id, { action: choice, refund_pct: choice === "refund" ? pct : 0, reviewer: name.trim(), note: note.trim() }, token);
      setReports(rows => rows.map(r => r.id === updated.id ? updated : r));
      setChoice(""); setNote("");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save decision."); }
    finally { setBusy(false); }
  }

  return <div className={styles.console}>
    <header className={styles.header}><div className={styles.brand}><Wordmark size={24} /><span className="t-label">Human review</span></div></header>
    <main className={styles.grid}>
      <section className={styles.zone}>
        <h1 className="t-heading-s">Review queue</h1>
        <label className="t-label" htmlFor="review-key">Reviewer access key</label>
        <input id="review-key" type="password" autoComplete="off" className={flow.field} value={token} onChange={e => setToken(e.target.value)} />
        <Button loading={busy} disabled={!token.trim()} onClick={load}>{loaded ? "Refresh queue" : "Open queue"}</Button>
        {error && <p className={flow.err} role="alert">{error}</p>}
        {loaded && !reports.length && <p className="t-body">No issues have been submitted.</p>}
        {reports.map(r => <Button key={r.id} variant={selected === r.id ? "primary" : "secondary"} onClick={() => select(r.id)}>
          {itemName(r.listing)} · {words(r.status)}
        </Button>)}
      </section>
      <section className={styles.zone} aria-label="Evidence report">
        {report ? <IssueReportView report={report} /> : <p className="t-body">Select a report to inspect the buyer’s statement and evidence.</p>}
      </section>
      <section className={`${styles.zone} ${styles.decision}`}>
        <h2 className="t-heading-s">Human decision</h2>
        {report && <>
          <p className="t-body-s">Inspection suggestion: {assessmentLabel[report.suggested_assessment]}. This is not a payment decision.</p>
          {report.status === "processing" ? <p className="t-body">Inspection is processing. Refresh the queue when it finishes.</p> : report.status === "resolved" ? <p className="t-body">This issue has been resolved. The recorded response is in the report.</p> : <>
            <fieldset className={styles.fieldset} disabled={busy}>
              <legend className="t-label">Choose an outcome</legend>
              {([['release', 'Release to seller'], ['refund', 'Refund buyer'], ['request_evidence', 'Request more evidence']] as const).map(([value, label]) => <label key={value} className={flow.row}>
                <input type="radio" name="human-decision" value={value} checked={choice === value} onChange={() => setChoice(value)} />{label}
              </label>)}
              {choice === "refund" && <><label className="t-label" htmlFor="refund-pct">Refund percentage</label><input id="refund-pct" type="number" min={1} max={100} className={flow.field} value={pct || ""} onChange={e => setPct(Number(e.target.value))} /></>}
              <label className="t-label" htmlFor="reviewer-name">Your name</label><input id="reviewer-name" className={flow.field} maxLength={120} value={name} onChange={e => setName(e.target.value)} />
              <label className="t-label" htmlFor="review-note">Reason or evidence request</label><textarea id="review-note" className={flow.field} rows={4} maxLength={2000} value={note} onChange={e => setNote(e.target.value)} />
            </fieldset>
            <Button loading={busy} disabled={!choice || !name.trim() || !note.trim() || (choice === "refund" && (!Number.isInteger(pct) || pct < 1 || pct > 100))} onClick={decide}>Record human decision</Button>
            <p className="t-caption">No outcome is selected by default. Only your recorded decision can settle an issue.</p>
          </>}
        </>}
      </section>
    </main>
  </div>;
}
