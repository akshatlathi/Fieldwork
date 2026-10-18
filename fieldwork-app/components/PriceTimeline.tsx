import styles from "./PriceTimeline.module.css";

export type PriceStep = {
  id: string;
  label: string;
  amount: string;
  by: string;
};

type Props = {
  steps: PriceStep[];
};

/* Offer -> Counter -> Agreed. The latest amount is large and uses Money blue (DESIGN.md 26). */
export function PriceTimeline({ steps }: Props) {
  const last = steps.length - 1;
  return (
    <ol className={styles.root} aria-label="Price history">
      {steps.map((s, i) => {
        const latest = i === last;
        return (
          <li key={s.id} className={`${styles.step} ${latest ? styles.latest : ""}`}>
            <span className={styles.rail} aria-hidden="true">
              <span className={styles.dot} />
              {i < last && <span className={styles.line} />}
            </span>
            <div className={styles.content}>
              <div className={styles.who}>
                <p className="t-overline">{s.label}</p>
                <p className={`${styles.by} t-body-s`}>{s.by}</p>
              </div>
              <p className={`${styles.amount} ${latest ? "t-num-xl" : "t-num-m"} tnum`}>
                {s.amount}
                {latest && <span className="sr-only"> (latest)</span>}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
