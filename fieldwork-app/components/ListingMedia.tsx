import { evidenceUrl, type ListingMedia as Media } from "@/lib/api";
import styles from "./Flow.module.css";

export function ListingMedia({ media, compact = false }: { media: Media[]; compact?: boolean }) {
  const selected = compact ? media.filter(m => m.kind === "photo").slice(0, 1) : media;
  if (!selected.length) return <p className="t-body-s t-secondary">{compact && media.some(m => m.kind === "video") ? "Seller video available · open listing to watch." : "No product media available for this listing."}</p>;
  return <div className={styles.evidenceGrid}>{selected.map(m => <figure key={m.url}>
    {m.kind === "video" ? <video controls playsInline preload="metadata" src={evidenceUrl(m.url)} aria-label={m.label} /> :
      <a href={evidenceUrl(m.url)} target="_blank" rel="noreferrer"><img src={evidenceUrl(m.url)} alt={m.label} loading="lazy" /></a>}
    <figcaption className="t-caption">{m.label}</figcaption>
  </figure>)}</div>;
}
