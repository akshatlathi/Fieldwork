import type { ReactNode } from "react";
import type { EvidenceState } from "@/lib/mock";
import { stateMeta } from "./stateMeta";
import styles from "./PhotoFrame.module.css";

export type Annotation = {
  /** Percentages of the frame. */
  x: number;
  y: number;
  w: number;
  h: number;
  state: EvidenceState;
  /** Short marker chip, e.g. "[01]" */
  marker?: string;
};

type Props = {
  /** Mono evidence label, e.g. "[01] BACK EDGE" */
  label?: string;
  ratio?: "4/3" | "1/1" | "3/4" | "16/9" | "16/10";
  tone?: "light" | "dark";
  /** e.g. "1/6" */
  counter?: string;
  caption?: ReactNode;
  annotation?: Annotation;
  /** Smaller marks and label for thumbnails. */
  compact?: boolean;
  /** Spoken description. The frame is a placeholder until real photos exist. */
  alt?: string;
  radius?: "card" | "feature";
};

/* Photo placeholder frame (DESIGN.md 12, 19.4): Inset surface, crop corners, mono label. No imagery. */
export function PhotoFrame({
  label,
  ratio = "4/3",
  tone = "light",
  counter,
  caption,
  annotation,
  compact = false,
  alt,
  radius = "feature",
}: Props) {
  const a = annotation;
  const meta = a ? stateMeta[a.state] : null;
  return (
    <figure className={styles.figure}>
      <div
        className={`${styles.frame} ${tone === "dark" ? styles.dark : ""} ${compact ? styles.compact : ""} ${
          radius === "card" ? styles.rCard : styles.rFeature
        }`}
        style={{ aspectRatio: ratio.replace("/", " / ") }}
        role="img"
        aria-label={alt ?? (label ? `Photo placeholder ${label}` : "Photo placeholder")}
      >
        <span className={`${styles.corner} ${styles.tl}`} aria-hidden="true" />
        <span className={`${styles.corner} ${styles.tr}`} aria-hidden="true" />
        <span className={`${styles.corner} ${styles.bl}`} aria-hidden="true" />
        <span className={`${styles.corner} ${styles.br}`} aria-hidden="true" />
        {!compact && <span className={styles.cross} aria-hidden="true" />}
        {label && <span className={`${styles.label} t-meta`}>{label}</span>}
        {counter && <span className={`${styles.counter} t-meta tnum`}>{counter}</span>}
        {a && meta && (
          <span
            className={styles.highlight}
            style={{
              left: `${a.x}%`,
              top: `${a.y}%`,
              width: `${a.w}%`,
              height: `${a.h}%`,
              borderColor: meta.fg,
            }}
            aria-hidden="true"
          >
            {a.marker && (
              <span
                className={`${styles.marker} t-meta`}
                style={{ background: meta.bg, color: meta.fg, borderColor: meta.border }}
              >
                {a.marker}
              </span>
            )}
          </span>
        )}
      </div>
      {caption && <figcaption className={`${styles.caption} t-body-s`}>{caption}</figcaption>}
    </figure>
  );
}
