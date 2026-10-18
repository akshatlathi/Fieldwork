"use client";
import { useEffect, useState } from "react";
import { getSellerDrafts, itemName, words, type SavedListing } from "@/lib/api";
import { useDraftState } from "@/lib/useDraftState";
import { Button } from "./Button";
import styles from "./Flow.module.css";

export function SavedListings() {
  const [listings, setListings] = useDraftState<SavedListing[]>("fw.sell.listings", []);
  const [error, setError] = useState("");
  useEffect(() => { let live = true; getSellerDrafts().then(rows => { if (live) setListings(rows); }).catch(e => { if (live) setError(e.message); });
    return () => { live = false; }; }, [setListings]);
  if (!listings.length && !error) return null;
  return <section className={styles.section} aria-label="Saved seller listings">
    <h2 className="t-heading-s">Saved listings</h2>
    <p className="t-caption t-secondary">Shared prototype listings. Resume a draft or open an existing listing.</p>
    {error && <p className={styles.err}>{error}</p>}
    {listings.map(listing => <div className={styles.card} key={listing.id}>
      <h3 className="t-heading-s">{itemName(listing)}</h3><p className="t-body-s">{words(listing.status)}</p>
      <Button variant="secondary" href={`/sell/review/${listing.id}`}>{listing.status === "published" ? "Open seller review" : "Resume draft"}</Button>
    </div>)}
  </section>;
}
