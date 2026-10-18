import type { ReactNode } from "react";
import { stateMeta } from "./stateMeta";
import type { HandoverResult } from "@/lib/mock";
import styles from "./ResultCard.module.css";

type Props = {
  variant: HandoverResult;
  /** Overrides the headline word, e.g. "Consistent". */
  word?: string;
  title: string;
  body: string;
  /** Evidence numbers, e.g. [{ value: "5/5", label: "checks" }, { value: "20 sec", label: "time" }] */
  stats?: { value: string; label: string }[];
  /** Annotated photo or other evidence shown inside the card. */
  media?: ReactNode;
  actions?: ReactNode;
};

const map = {
  matches: { state: "shown", word: "Matches" },
  differs: { state: "differs", word: "Differs" },
  "cant-tell": { state: "cant-tell", word: "Can't tell" },
} as const;

/* Handover result (DESIGN.md 27, Recipe D). Dominant, not theatrical: no confetti, no check explosion. */
export function ResultCard({ variant, word, title, body, stats, media, actions }: Props) {
  const m = stateMeta[map[variant].state];
  const Icon = m.Icon;
  return (
    <section
      className={`${styles.card} ${styles[variant]}`}
      role="status"
      aria-label={`Result: ${word ?? map[variant].word}`}
      data-result={variant}
    >
      <div className={styles.head}>
        <span className={styles.icon} aria-hidden="true">
          <Icon size={24} strokeWidth={2} />
        </span>
        <p className={`${styles.word} t-overline`}>{word ?? map[variant].word}</p>
      </div>
      <h2 className={`${styles.title} t-heading-l`}>{title}</h2>
      <p className={`${styles.body} t-body`}>{body}</p>

      {media && <div className={styles.media}>{media}</div>}

      {stats && stats.length > 0 && (
        <dl className={styles.stats}>
          {stats.map((s) => (
            <div key={s.label} className={styles.stat}>
              <dt className="t-caption">{s.label}</dt>
              <dd className={`${styles.value} t-num-m tnum`}>{s.value}</dd>
            </div>
          ))}
        </dl>
      )}

      {actions && <div className={styles.actions}>{actions}</div>}
    </section>
  );
}
