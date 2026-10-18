import type { ReactNode } from "react";
import styles from "./ActionBar.module.css";

/* Sticky bottom bar: one primary action per screen (DESIGN.md 47.13). */
export function ActionBar({ children, note }: { children: ReactNode; note?: ReactNode }) {
  return (
    <div className={styles.bar}>
      {children}
      {note && <p className={`${styles.note} t-caption`}>{note}</p>}
    </div>
  );
}
