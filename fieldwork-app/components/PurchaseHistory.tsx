"use client";
import { useEffect, useState } from "react";
import { getPurchases, issueStatusText, itemName, paymentStatusText, rememberMandate, yen, type Purchase } from "@/lib/api";
import { useDraftState } from "@/lib/useDraftState";
import { Button } from "./Button";
import { StatusTag } from "./StatusTag";
import styles from "./Flow.module.css";

export function PurchaseHistory() {
  const [purchases, setPurchases] = useDraftState<Purchase[] | null>("fw.buy.purchases", null);
  const [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    const refresh = async () => {
      try {
        const rows = await getPurchases();
        if (!live) return;
        setPurchases(rows); setError("");
        // Most recent purchase per item wins when recovering an older browser session.
        const seen = new Set<string>();
        for (const row of rows) if (!seen.has(row.item_id)) { seen.add(row.item_id); rememberMandate(row.item_id, row); }
      } catch (e) { if (live) setError(e instanceof Error ? e.message : "Could not load purchases."); }
    };
    void refresh(); const timer = setInterval(refresh, 10000);
    window.addEventListener("fw-purchases-updated", refresh);
    return () => { live = false; clearInterval(timer); window.removeEventListener("fw-purchases-updated", refresh); };
  }, [setPurchases]);
  const card = (purchase: Purchase) => <article className={styles.card} key={purchase.id}>
    <div className={styles.between}><h3 className="t-heading-s">{itemName(purchase)}</h3><span className="t-num-m">{yen(purchase.amount, purchase.currency)}</span></div>
    <StatusTag state={purchase.status === "held" ? "money" : "shown"} label={paymentStatusText(purchase.status)} />
    {purchase.issue_status && <p className="t-body-s">Issue: {issueStatusText(purchase.issue_status)}.</p>}
    <p className="t-meta">{purchase.id} · {new Date(purchase.created_at * 1000).toLocaleString()}</p>
    <Button variant="secondary" href={purchase.issue_id ? `/case/${purchase.item_id}?issue=${purchase.issue_id}` : `/unbox/${purchase.item_id}?m=${purchase.id}`}>
      {purchase.issue_id ? "Open review report" : purchase.status === "held" ? "Check received garment" : "Open purchase"}
    </Button>
  </article>;
  return <section className={styles.section} aria-labelledby="purchases-title">
    <h2 className="t-heading-s" id="purchases-title">Saved purchases</h2>
    <p className="t-caption t-secondary">Shared prototype purchase history · simulated payments. Saved purchases remain here after switching tabs or reloading.</p>
    {error && <p className={styles.err} role="alert">{error}</p>}
    {purchases === null ? <p role="status">Loading purchases…</p> : !purchases.length ? <p className="t-body-s">No purchases yet.</p> : <>
      {purchases.slice(0, 3).map(card)}
      {purchases.length > 3 && <details className={styles.details}><summary>Earlier purchases ({purchases.length - 3})</summary><div className={styles.section}>{purchases.slice(3).map(card)}</div></details>}
    </>}
  </section>;
}
