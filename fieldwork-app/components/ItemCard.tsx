import Link from "next/link";
import type { ReactNode } from "react";
import type { NearbyItem } from "@/lib/mock";
import { CoverageSummary } from "./CoverageSummary";
import { PhotoFrame } from "./PhotoFrame";
import styles from "./ItemCard.module.css";

/* Item card (Recipe A, compact list variant): photo, title + price, attributes, one evidence strip. */
export function ItemCard({ item }: { item: NearbyItem }) {
  /* Only the iPhone 13 has a full item page in this first build. */
  const linked = item.slug === "iphone-13";
  const label = `${item.title}, ${item.price}, ${item.shown} of ${item.total} claims shown`;
  const content: ReactNode = (
    <>
      <div className={styles.photo}>
        <PhotoFrame label={item.photoLabel} ratio="1/1" compact radius="card" />
      </div>
      <div className={styles.body}>
        <div className={styles.titleRow}>
          <h3 className="t-body">{item.title}</h3>
          <p className="t-heading-s tnum">{item.price}</p>
        </div>
        <p className={`${styles.attrs} t-body-s tnum`}>{item.attrs}</p>
        <p className={`${styles.where} t-caption`}>{item.where}</p>
        <CoverageSummary shown={item.shown} total={item.total} variant="strip" />
      </div>
    </>
  );
  if (linked) {
    return (
      <Link href={`/item/${item.slug}`} className={styles.card} aria-label={label}>
        {content}
      </Link>
    );
  }
  return (
    <article className={`${styles.card} ${styles.static}`} aria-label={label}>
      {content}
    </article>
  );
}
