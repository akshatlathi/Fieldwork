"use client";

import { useId, useState, type ReactNode } from "react";
import type { Claim } from "@/lib/mock";
import { PhotoFrame } from "./PhotoFrame";
import { StatusTag } from "./StatusTag";
import { stateMeta } from "./stateMeta";
import styles from "./ClaimRow.module.css";

type Props = {
  claim: Claim;
  density?: "default" | "compact";
  /** Shows a "See photo" control that opens the evidence photo inline. */
  seePhoto?: boolean;
  /** Optional action under the row, e.g. "Add photo". */
  action?: ReactNode;
};

/* Claim row anatomy (DESIGN.md 19.1): [icon] claim .... [state] / support / source / [See photo] */
export function ClaimRow({ claim, density = "default", seePhoto = true, action }: Props) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const m = stateMeta[claim.state];
  const Icon = m.Icon;
  const canSee = seePhoto && !!claim.photoLabel && claim.state !== "not-shown";

  return (
    <li className={`${styles.row} ${density === "compact" ? styles.compact : ""}`} data-state={claim.state}>
      <span className={styles.icon} style={{ color: m.fg }}>
        <Icon size={20} strokeWidth={2} aria-hidden="true" />
      </span>
      <div className={styles.body}>
        <div className={styles.head}>
          <h3 className={`${styles.title} t-body`}>{claim.title}</h3>
          <StatusTag state={claim.state} label={claim.stateLabel} size="sm" />
        </div>
        {claim.support && <p className={`${styles.support} t-body-s`}>{claim.support}</p>}
        {claim.source && <p className={`${styles.source} t-meta`}>{claim.source}</p>}
        {claim.state === "not-shown" && (
          <p className={`${styles.source} t-meta`}>No evidence captured for this claim.</p>
        )}
        {canSee && (
          <button
            type="button"
            className={`${styles.see} t-label`}
            aria-expanded={open}
            aria-controls={panelId}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? "Hide photo" : "See photo"}
            <span className="sr-only"> for {claim.title}</span>
          </button>
        )}
        {action}
        {canSee && open && (
          <div id={panelId} className={styles.photo}>
            <PhotoFrame
              label={claim.photoLabel}
              ratio="16/9"
              radius="card"
              caption={claim.source}
              annotation={
                claim.state === "differs"
                  ? { x: 18, y: 22, w: 30, h: 28, state: "differs", marker: "[01]" }
                  : undefined
              }
            />
          </div>
        )}
      </div>
    </li>
  );
}

export function ClaimList({ children, label }: { children: ReactNode; label: string }) {
  return (
    <ul className={styles.list} aria-label={label}>
      {children}
    </ul>
  );
}
