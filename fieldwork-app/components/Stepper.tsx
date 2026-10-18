import { Check } from "lucide-react";
import styles from "./Stepper.module.css";

type Props = {
  steps: string[];
  /** Zero-based index of the current step. Steps before it are done. Use steps.length for "all done". */
  current: number;
  /** "segments" is a quiet bar row (camera). "labelled" shows the step names (handover). */
  variant?: "segments" | "labelled";
  onDark?: boolean;
  label?: string;
};

export function Stepper({ steps, current, variant = "labelled", onDark = false, label = "Progress" }: Props) {
  const shownIndex = Math.min(current + 1, steps.length);
  return (
    <ol
      className={`${styles.root} ${styles[variant]} ${onDark ? styles.onDark : ""}`}
      aria-label={`${label}: step ${shownIndex} of ${steps.length}`}
    >
      {steps.map((s, i) => {
        const status = i < current ? "done" : i === current ? "current" : "todo";
        return (
          <li
            key={s}
            className={`${styles.step} ${styles[status]}`}
            aria-current={status === "current" ? "step" : undefined}
          >
            <span className={styles.bar} aria-hidden="true" />
            {variant === "labelled" && (
              <span className={`${styles.name} t-label`}>
                {status === "done" ? (
                  <Check size={16} strokeWidth={2} aria-hidden="true" />
                ) : (
                  <span className={`${styles.index} t-meta`}>{String(i + 1).padStart(2, "0")}</span>
                )}
                {s}
                <span className="sr-only">{status === "done" ? ", done" : status === "current" ? ", current" : ""}</span>
              </span>
            )}
            {variant === "segments" && <span className="sr-only">{s}</span>}
          </li>
        );
      })}
    </ol>
  );
}
