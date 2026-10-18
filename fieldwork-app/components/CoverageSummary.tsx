import styles from "./CoverageSummary.module.css";

type Props = {
  shown: number;
  total: number;
  /** "strip" is a one-line version for cards. "full" is larger, for the Evidence tab. */
  variant?: "strip" | "full";
  /** Optional trailing detail, e.g. "battery 87% (read from screen)" */
  detail?: string;
};

/* Coverage: thin segmented progress + numerals. Never a percentage score (DESIGN.md 19.3). */
export function CoverageSummary({ shown, total, variant = "strip", detail }: Props) {
  const text = `${shown} of ${total} claims shown`;
  return (
    <div className={`${styles.root} ${variant === "full" ? styles.full : ""}`}>
      <div
        className={styles.bar}
        role="img"
        aria-label={`${text} in photos`}
        style={{ gridTemplateColumns: `repeat(${total}, 1fr)` }}
      >
        {Array.from({ length: total }).map((_, i) => (
          <span key={i} className={i < shown ? styles.on : styles.off} />
        ))}
      </div>
      <p className={`${styles.text} ${variant === "full" ? "t-body" : "t-label"} tnum`}>
        <span className={styles.strong}>{text}</span>
        {detail && <span className={`${styles.detail} t-secondary`}> · {detail}</span>}
      </p>
    </div>
  );
}
