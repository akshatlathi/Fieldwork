import type { ReactNode } from "react";
import { ActorTag } from "./ActorTag";
import styles from "./OutcomeCard.module.css";

type Props = {
  caseId: string;
  saw: string;
  rule: string;
  ruleLabel?: string;
  decision: string;
  reviewer: { name: string; role: string };
  appeal: string;
  /** Appeal control, rendered under the appeal sentence. */
  appealAction?: ReactNode;
};

/*
  Outcome card (DESIGN.md 29, Recipe E). Four sections, three distinct actors:
  AI analysis (observed), Rule (what applies), Human review (who decides).
*/
export function OutcomeCard({ caseId, saw, rule, ruleLabel = "Rule 4.2", decision, reviewer, appeal, appealAction }: Props) {
  return (
    <article className={styles.card} aria-label={`Outcome for case ${caseId}`}>
      <header className={styles.header}>
        <h2 className="t-heading-m">Case reviewed</h2>
        <p className="t-meta t-quiet">CASE #{caseId}</p>
      </header>

      <section className={styles.section}>
        <p className="t-overline t-secondary">What we saw</p>
        <ActorTag kind="ai" title="AI analysis" />
        <p className="t-body">{saw}</p>
      </section>

      <section className={styles.section}>
        <p className="t-overline t-secondary">The rule</p>
        <ActorTag kind="rule" title={ruleLabel} />
        <p className="t-body">{rule}</p>
      </section>

      <section className={`${styles.section} ${styles.decision}`}>
        <p className="t-overline t-secondary">Decision</p>
        <ActorTag kind="human" title="Human review" detail={`${reviewer.name} · ${reviewer.role}`} />
        <p className="t-heading-s">{decision}</p>
      </section>

      <section className={styles.section}>
        <p className="t-overline t-secondary">Appeal</p>
        <p className="t-body">{appeal}</p>
        {appealAction}
      </section>
    </article>
  );
}
