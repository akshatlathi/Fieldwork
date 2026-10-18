import type { CSSProperties } from "react";
import type { EvidenceState } from "@/lib/mock";
import { stateMeta } from "./stateMeta";
import styles from "./StatusTag.module.css";

type Props = {
  state: EvidenceState;
  /** Overrides the default words, e.g. "Read from screen". Always keep text: colour is never the only signal. */
  label?: string;
  size?: "sm" | "md";
};

export function StatusTag({ state, label, size = "md" }: Props) {
  const m = stateMeta[state];
  const style = { "--tag-fg": m.fg, "--tag-bg": m.bg, "--tag-border": m.border } as CSSProperties;
  const Icon = m.Icon;
  return (
    <span className={`${styles.tag} ${styles[size]} t-label`} style={style} data-state={state}>
      <Icon size={size === "sm" ? 14 : 16} strokeWidth={2} aria-hidden="true" />
      <span>{label ?? m.label}</span>
    </span>
  );
}
