import { ScrollText } from "lucide-react";
import styles from "./ActorTag.module.css";

type Props = {
  kind: "ai" | "rule" | "human";
  /** e.g. "AI analysis", "Rule 4.2", "Human review" */
  title: string;
  /** e.g. "Meera · Trust & Safety" */
  detail?: string;
};

/*
  The three actors must look different (DESIGN.md 22):
  AI = small square "AI" label, System = rule/document marker, Human = round avatar with name + role.
*/
export function ActorTag({ kind, title, detail }: Props) {
  return (
    <span className={styles.actor} data-kind={kind}>
      {kind === "ai" && (
        <span className={`${styles.ai} t-meta`} aria-hidden="true">
          AI
        </span>
      )}
      {kind === "rule" && (
        <span className={styles.rule} aria-hidden="true">
          <ScrollText size={14} strokeWidth={2} />
        </span>
      )}
      {kind === "human" && (
        <span className={`${styles.human} t-label`} aria-hidden="true">
          {(detail ?? title).trim().charAt(0).toUpperCase()}
        </span>
      )}
      <span className={`${styles.text} t-label`}>
        <span>{title}</span>
        {detail && <span className={styles.detail}> · {detail}</span>}
      </span>
    </span>
  );
}
