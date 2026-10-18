"use client";
import { useEffect, useState } from "react";
import { getIssues, issueStatusText, itemName, type IssueReport } from "@/lib/api";
import { TopBar } from "@/components/TopBar";
import { BottomNav } from "@/components/BottomNav";
import { Button } from "@/components/Button";
import { StatusTag } from "@/components/StatusTag";
import styles from "@/components/Flow.module.css";

export default function HelpPage() {
  const [reports, setReports] = useState<IssueReport[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    const refresh = () => getIssues().then(data => { if (live) { setReports(data); setError(""); } })
      .catch(e => { if (live) setError(e.message); });
    void refresh(); const timer = setInterval(refresh, 10000);
    return () => { live = false; clearInterval(timer); };
  }, []);
  return <><TopBar title="Help and issue history" backHref="/" /><main className={styles.main}>
    <p className="t-body-s t-secondary">Shared local prototype history. Open a report to see its evidence, review status, and any response from a human reviewer.</p>
    {error && <p className={styles.err} role="alert">{error}</p>}
    {reports === null && !error && <p role="status">Loading issue reports…</p>}
    {reports?.length === 0 && <p>No issues have been raised yet. Open your purchase to check the received garment.</p>}
    {reports?.map(report => <section className={styles.card} key={report.id}>
      <StatusTag state={report.status === "resolved" ? "shown" : "pending"} label={issueStatusText(report.status)} />
      <h2 className="t-heading-s">{itemName(report.listing)}</h2>
      <p className="t-body-s">{report.buyer_text || "Received-garment issue"}</p>
      <p className="t-meta">{new Date(report.updated_at).toLocaleString()} · {report.id}</p>
      <Button href={`/case/${report.item_id}?issue=${encodeURIComponent(report.id)}`} variant="secondary">Open report</Button>
    </section>)}
  </main><BottomNav /></>;
}
