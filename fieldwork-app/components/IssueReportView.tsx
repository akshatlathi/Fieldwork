"use client";

import { BlinkComparator } from "./BlinkComparator";
import { StatusTag } from "./StatusTag";
import { decisionText, evidenceUrl, issueStatusText, itemName, sentence, words, yen, type IssueReport } from "@/lib/api";
import { FormattedText } from "./FormattedText";
import styles from "./Flow.module.css";

export const assessmentLabel = {
  consistent: "The photos look like they match the listing",
  differs: "The photos may show something different from the listing",
  cant_tell: "The photos are not clear enough to tell",
};

export function IssueReportView({ report }: { report: IssueReport }) {
  const comparisons = report.inspection?.comparisons ?? [];
  const crops = comparisons.filter(pair => pair.kind !== "aligned_view");
  const focused = (crops.length ? crops : comparisons).slice(0, 3);
  const remaining = comparisons.filter(pair => !focused.includes(pair));
  const comparison = (pair: typeof comparisons[number], i: number) => <section className={styles.card} key={`pair-${i}`}>
    <h3 className="t-heading-s">{words(pair.what)}</h3>
    {pair.listing_crop && pair.unbox_crop && <BlinkComparator listingSrc={evidenceUrl(pair.listing_crop)} unboxSrc={evidenceUrl(pair.unbox_crop)}
      listingLabel={pair.listing_label ?? (pair.listing_frame_id ? `Listing view ${pair.listing_frame_id}` : undefined)}
      unboxLabel={pair.received_label ?? undefined} />}
    <FormattedText text={sentence(pair.reason)} />
    {(pair.unsure || pair.comparable === false) && <p className="t-body-s">These views do not support a definite comparison. A human must inspect the original evidence.</p>}
  </section>;
  return <>
    <section className={styles.card} aria-label="Human review status">
      <StatusTag state={report.status === "resolved" ? "shown" : "pending"} label={issueStatusText(report.status)} />
      <h2 className="t-heading-s">{itemName(report.listing)}</h2>
      <p className="t-meta">Report {report.id} · {new Date(report.created_at).toLocaleString()}</p>
      {report.amount !== null && <p className="t-body-s">Simulated escrow: {yen(report.amount, report.currency)}{report.status !== "resolved" ? " · payment on hold until a person checks" : " · a person has decided"}</p>}
      <p className="t-body-s">{report.status === "processing" ? "Your issue is saved. We are checking the photos now." : report.status === "resolved" ? "A person has made a decision. See their answer below." : "Your issue is waiting for a person to check. The automatic check does not decide who gets paid."}</p>
    </section>
    <section className={styles.card}>
      <h2 className="t-heading-s">Buyer’s statement</h2>
      <p className="t-body">{report.buyer_text || "No written description supplied."}</p>
      <p className="t-caption t-secondary">Reported by the buyer; not an established finding.</p>
    </section>
    <section className={styles.card}>
      <h2 className="t-heading-s">What the automatic check suggests</h2>
      {report.inspection && report.inspection.policy_version !== "region-correspondence-v1" && <p className="t-body-s">This older inspection predates the region correspondence checks. Its crop comparisons need human review; a new evidence submission uses the updated checks.</p>}
      <p className="t-body">{assessmentLabel[report.suggested_assessment]}</p>
      <FormattedText text={report.summary} />
      <h3 className="t-label">Limits of this inspection</h3>
      <ul className={styles.bullets}>{[...new Set(report.limitations)].map((text, i) => <li key={i} className="t-body-s">{sentence(text)}</li>)}</ul>
      {report.inspection?.closeup_request && <p className="t-body-s">Suggested close-up: {words(report.inspection.closeup_request)}. A person will decide whether we need another photo.</p>}
    </section>
    {report.inspection?.findings.map((finding, i) => <section className={styles.card} key={`finding-${i}`}>
      <h3 className="t-heading-s">{words(finding.what)}</h3>
      <p className="t-meta">{finding.listing_label ?? finding.listing_frame_id ?? "Listing source not labelled in this older report"} · {finding.received_label ?? finding.received_frame_id ?? "Received source not labelled in this older report"}</p>
      {finding.listing_crop && finding.unbox_crop && <BlinkComparator listingSrc={evidenceUrl(finding.listing_crop)} unboxSrc={evidenceUrl(finding.unbox_crop)} listingLabel={finding.listing_label ?? undefined} unboxLabel={finding.received_label ?? undefined} />}
      <FormattedText text={sentence(finding.reason)} />
    </section>)}
    {focused.map(comparison)}
    {!!remaining.length && <details className={styles.details}>
      <summary className="t-label">More comparison evidence ({remaining.length})</summary>
      <div className={styles.section}>{remaining.map(comparison)}</div>
    </details>}
    <details className={styles.details}>
      <summary className="t-label">Original evidence</summary>
      <div className={styles.evidenceGrid}>{report.media.map((media, i) => <figure key={i}>
        {/\.(mp4|webm|mov)$/i.test(media.url) ? <video controls preload="metadata" src={evidenceUrl(media.url)} /> : <img src={evidenceUrl(media.url)} alt={media.label} loading="lazy" />}
        <figcaption className="t-caption">{media.label}</figcaption>
      </figure>)}</div>
    </details>
    {report.decision && <section className={styles.card}>
      <h2 className="t-heading-s">Reviewer’s answer</h2>
      <p className="t-body">{decisionText(report.decision, report.amount, report.currency)}</p>
      <p className="t-body">{report.decision.note}</p><p className="t-meta">{report.decision.reviewer}</p>
    </section>}
  </>;
}
