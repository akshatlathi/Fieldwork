import { Circle, CircleCheck, CircleDot } from "lucide-react";
import styles from "./AIActivity.module.css";

export type ActivityItem = {
  id: string;
  label: string;
  status: "done" | "active" | "pending";
};

type Props = {
  /** Current task in plain words, e.g. "Reading battery and storage…" */
  title: string;
  items?: ActivityItem[];
  /** Source line, e.g. "Source · Settings screenshot" */
  source?: string;
  /** Meaningful progress only. 0 to 1. Omit when unknown. */
  progress?: number;
  variant?: "card" | "plain";
  onDark?: boolean;
};

/*
  AI activity (DESIGN.md 21, Recipe C): AI is a behaviour, not a colour.
  Small "AI" label + task + progressive checklist + source. No chat bubbles, no sparkles, no spinning logo.
*/
export function AIActivity({ title, items, source, progress, variant = "card", onDark = false }: Props) {
  const done = items ? items.filter((i) => i.status === "done").length : 0;
  const p = progress ?? (items && items.length ? done / items.length : undefined);
  const circumference = 2 * Math.PI * 8;

  return (
    <div
      className={`${styles.root} ${variant === "card" ? styles.card : styles.plain} ${onDark ? styles.onDark : ""}`}
      aria-live="polite"
    >
      <div className={styles.head}>
        <span className={`${styles.label} t-meta`}>AI</span>
        <p className={`${styles.title} t-body`}>{title}</p>
        {p !== undefined && (
          <svg
            className={styles.ring}
            width="24"
            height="24"
            viewBox="0 0 24 24"
            role="img"
            aria-label={items ? `${done} of ${items.length} steps done` : `${Math.round(p * 100)} percent`}
          >
            <circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" strokeOpacity="0.2" strokeWidth="2" />
            <circle
              className={styles.arc}
              cx="12"
              cy="12"
              r="8"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={circumference * (1 - p)}
              transform="rotate(-90 12 12)"
            />
          </svg>
        )}
      </div>

      {items && (
        <ul className={styles.list}>
          {items.map((it) => (
            <li key={it.id} className={`${styles.item} ${styles[it.status]} t-body-s`}>
              {it.status === "done" && <CircleCheck size={20} strokeWidth={2} aria-hidden="true" />}
              {it.status === "active" && <CircleDot size={20} strokeWidth={2} aria-hidden="true" />}
              {it.status === "pending" && <Circle size={20} strokeWidth={2} aria-hidden="true" />}
              <span className={styles.text}>{it.label}</span>
              <span className="sr-only">
                {it.status === "done" ? ", done" : it.status === "active" ? ", in progress" : ", waiting"}
              </span>
            </li>
          ))}
        </ul>
      )}

      {source && <p className={`${styles.source} t-meta`}>{source}</p>}
    </div>
  );
}
