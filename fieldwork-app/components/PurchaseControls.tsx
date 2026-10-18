"use client";
import { createEscrow, makeOffer, rememberMandate, yen, type Offer } from "@/lib/api";
import { Button } from "./Button";
import { useDraftState } from "@/lib/useDraftState";
import { useBought } from "@/lib/useBought";
import styles from "./Flow.module.css";

export function PurchaseControls({ itemId, askingPrice, negotiationEnabled = false }: {
  itemId: string; askingPrice: number | null; negotiationEnabled?: boolean;
}) {
  const [amount, setAmount] = useDraftState(`fw.purchase.${itemId}.amount`, "");
  const [offer, setOffer] = useDraftState<Offer | null>(`fw.purchase.${itemId}.offer`, null);
  const [busy, setBusy] = useDraftState(`fw.purchase.${itemId}.busy`, false, false);
  const [held, setHeld] = useDraftState(`fw.purchase.${itemId}.held`, false, false);
  const [error, setError] = useDraftState(`fw.purchase.${itemId}.error`, "");
  async function purchase(price: number, quoteId?: string) {
    setBusy(true); setError("");
    try { const mandate = await createEscrow(itemId, price, "INR", quoteId); rememberMandate(itemId, mandate); setHeld(true); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not create escrow."); }
    finally { setBusy(false); }
  }
  const bought = useBought(itemId);
  if (bought) return <div className={styles.section}><p role="status"><strong>You bought this</strong></p><Button href={bought.href}>View your purchase</Button></div>;
  if (!askingPrice) return <p className="t-body-s">The seller must set an asking price before purchase.</p>;
  if (held) return <div className={styles.section}><p role="status">Simulated payment is on hold. It goes to the seller when you accept delivery, or a person decides if you report an issue.</p><Button href={`/unbox/${itemId}`}>Check received garment</Button></div>;
  return <div className={styles.section}>
    {error && <p className={styles.err} role="alert">{error}</p>}
    <Button loading={busy} onClick={() => purchase(askingPrice)}>Confirm purchase · hold {yen(askingPrice, "INR")}</Button>
    <p className="t-caption t-secondary">Demo payment · no real money is charged.</p>
    {negotiationEnabled && <>
      <label className="t-label" htmlFor={`offer-${itemId}`}>Make an offer (INR)</label>
      <input id={`offer-${itemId}`} className={styles.field} inputMode="numeric" type="number" min={1} step={1} value={amount} onChange={e => setAmount(e.target.value)} />
      <Button variant="secondary" disabled={busy || !Number.isInteger(Number(amount)) || Number(amount) <= 0 || (offer?.round ?? 0) >= 5} onClick={async () => {
        setBusy(true); setError("");
        try { setOffer(await makeOffer(itemId, Number(amount), offer?.negotiation_id)); }
        catch (e) { setError(e instanceof Error ? e.message : "Could not submit offer."); }
        finally { setBusy(false); }
      }}>Send offer to seller agent</Button>
      {offer && <div className={styles.card} role="status">
        <p className="t-body-s">{offer.status === "accepted" ? "Seller accepts" : offer.status === "fixed" ? "Seller’s fixed price" : "Seller counters"}: {yen(offer.price, "INR")}.</p>
        {offer.round && <p className="t-meta">Round {offer.round} of {offer.max_rounds} · quote valid for 30 minutes</p>}
        <Button disabled={busy} onClick={() => purchase(offer.price, offer.quote_id)}>Accept and hold {yen(offer.price, "INR")}</Button>
      </div>}
    </>}
  </div>;
}
