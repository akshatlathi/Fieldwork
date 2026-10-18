import { Logo } from "./Logo";
import styles from "./EvidenceBadge.module.css";

type Props = {
  variant?: "compact" | "expanded";
  angles?: number;
  markers?: number;
};

/* Guided evidence captured. It never says what the badge must not claim (see DESIGN.md 19.2). */
export function EvidenceBadge({ variant = "compact", angles = 5, markers = 1 }: Props) {
  if (variant === "compact") {
    return (
      <span className={`${styles.compact} t-label`}>
        <Logo size={16} monochrome />
        Evidence
      </span>
    );
  }
  return (
    <section className={styles.expanded} aria-label="Evidence badge">
      <span className={styles.mark}>
        <Logo size={24} />
      </span>
      <div className={styles.body}>
        <h2 className="t-heading-s">Evidence captured</h2>
        <ul className={`${styles.list} t-body-s t-secondary`}>
          <li>
            <span className="tnum">{angles}</span> guided angles
          </li>
          <li>
            <span className="tnum">{markers}</span> unit identity {markers === 1 ? "marker" : "markers"}
          </li>
        </ul>
      </div>
    </section>
  );
}
