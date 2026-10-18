import styles from "./mobile-layout.module.css";

/* Mobile-first column. On wide screens, a centred 390px column on a Parchment canvas. */
export default function MobileLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className={styles.canvas}>
      <div className={styles.column}>{children}</div>
    </div>
  );
}
