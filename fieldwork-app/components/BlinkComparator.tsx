import styles from "./Flow.module.css";

/* Keep both sources visible: automatic flickering hides mismatches and labels. */
export function BlinkComparator({ listingSrc, unboxSrc, listingLabel = "Listing image · source label unavailable", unboxLabel = "Received image · source label unavailable" }: {
  listingSrc: string; unboxSrc: string; listingLabel?: string; unboxLabel?: string;
}) {
  return <div className={styles.evidenceGrid} aria-label="Listing and received evidence side by side">
    {[{ src: listingSrc, label: listingLabel }, { src: unboxSrc, label: unboxLabel }].map((image, i) => <figure key={i}>
      <a href={image.src} target="_blank" rel="noreferrer"><img src={image.src} alt={image.label} loading="lazy" /></a>
      <figcaption className="t-caption">{image.label}</figcaption>
    </figure>)}
  </div>;
}
