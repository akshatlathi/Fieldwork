/* Typed client for the Fieldwork FastAPI service (fieldwork-ai/fieldwork/api.py). */

export const API_BASE = (process.env.NEXT_PUBLIC_FIELDWORK_PREVIEW === "1" ? "/api/preview" : process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000").replace(/\/$/, "");

export type Lane = "shown" | "measured" | "declared" | "cant_judge";
export type Severity = "none" | "minor" | "major";

export type Box = { frame_id: string; box_2d: [number, number, number, number] }; // ymin, xmin, ymax, xmax in 0-1000
export type Claim = {
  id: string;
  lane: Lane;
  code: string;
  region: string;
  severity: Severity;
  note: string;
  evidence: Box[];
  value: number | null;
  error: number | null;
};
export type ConditionRecord = {
  spec: string;
  id: string;
  item: { type: string; brand: string | null; size_label: string | null; colour: string | null; material: string | null };
  claims: Claim[];
  grade_set: number[];
  price_band: [number, number] | null;
  currency: string;
  capture: { code_seen: boolean; frames: string[]; created_at: string };
  listing_text_en: string;
};
export type ListingMedia = { kind: "photo" | "video"; label: string; url: string };
export type Listing = { id: string; en: string; evidence_badge?: string;
  media?: ListingMedia[]; asking_price?: number | null; purchase_price?: number | null;
  price_source?: string; currency?: string; negotiation_enabled?: boolean;
  seller_managed?: boolean;
  purchase_available?: boolean;
  publication_status?: string; seller_limitations?: string[];
  capture_coverage?: { views: { region: string; status: string; note: string; evidence: Box[] }[];
    needs_more_evidence: boolean; guidance: string[]; limitation: string };
  [lang: string]: unknown };
export type Answer = { answer: string; lang: string; state: "shown" | "not_in_take" | "cant_judge" | string; claim_ids: string[] };
export type ToolCall = { tool: string; args: Record<string, unknown>; result?: unknown };
export type AgentReply = { text: string; tool_calls: ToolCall[]; model: string };
export type SearchCard = {
  id: string;
  item: ConditionRecord["item"];
  grade_set: number[];
  price_band: [number, number] | null;
  currency: string;
  shown_flaws: { code: string; region: string; severity: string }[];
  declared_flaws?: { code: string; region: string; severity: string }[];
  cant_judge: string[];
  evidence_badge: string;
  summary_line: string;
  media?: ListingMedia[]; purchase_price?: number | null; price_source?: string; negotiation_enabled?: boolean;
};
export type Finding = {
  kind: string;
  what: string;
  region_box: number[];
  listing_crop: string | null;
  unbox_crop: string | null;
  reason: string;
  listing_label?: string | null; received_label?: string | null;
  listing_frame_id?: string | null; received_frame_id?: string | null; comparable?: boolean;
};
export type UnboxResult = {
  policy_version?: string;
  verdict: "consistent" | "differs" | "cant_tell";
  findings: Finding[];
  closeup_request: string | null;
  pairs_aligned: number;
  pairs_total: number;
  flags: string[];
};
export type HumanDecision = {
  action: "release" | "refund" | "request_evidence";
  refund_pct: number;
  reviewer: string;
  note: string;
};
export type IssueReport = {
  id: string;
  item_id: string;
  mandate_id: string | null;
  created_at: string;
  updated_at: string;
  status: "processing" | "awaiting_review" | "needs_evidence" | "resolved";
  buyer_text: string;
  listing: ConditionRecord;
  amount: number | null;
  currency: string;
  suggested_assessment: "consistent" | "differs" | "cant_tell";
  summary: string;
  limitations: string[];
  inspection: (UnboxResult & { comparisons: (Finding & { unsure?: boolean; new_defect?: boolean })[] }) | null;
  media: { label: string; url: string }[];
  history: Record<string, unknown>[];
  decision: (HumanDecision & { at: string }) | null;
};
export type Mandate = {
  id: string;
  item_id: string;
  payer: string;
  payee: string;
  amount: number;
  currency: string;
  status: "held" | "released" | "refunded" | "partial" | string;
  events: Record<string, unknown>[];
};
export type Purchase = Pick<Mandate, "id" | "item_id" | "amount" | "currency" | "status"> & {
  item: ConditionRecord["item"]; created_at: number; issue_id: string | null; issue_status: string | null;
};
export type SavedListing = { id: string; status: string; item: ConditionRecord["item"];
  asking_price: number | null; currency: string; updated_at: string };

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(0, "Can't reach the Fieldwork service. It may be waking up or busy; wait 30 seconds and try again.");
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : Array.isArray(j.detail) ? j.detail.map((error: { msg?: string }) => error.msg ?? "Check the supplied values.").join(" ") : "The service could not complete this request.";
    } catch {}
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

function videoName(b?: Blob | null) {
  if (b?.type.includes("quicktime")) return "take.mov";
  return b && b.type.includes("mp4") ? "take.mp4" : "take.webm";
}
function form(fields: Record<string, string>, video?: Blob | null, photos?: File[]) {
  const f = new FormData();
  for (const [k, v] of Object.entries(fields)) f.append(k, v);
  if (video) f.append("video", video, videoName(video));
  for (const p of photos ?? []) f.append("photos", p, p.name);
  return f;
}

export const getRecord = (id: string) => call<ConditionRecord>(`/records/${encodeURIComponent(id)}`);
export const getListing = (id: string) => call<Listing>(`/listings/${encodeURIComponent(id)}`);
export const searchGarments = () => call<SearchCard[]>("/search");
export const recordUrl = (id: string) => `${API_BASE}/records/${encodeURIComponent(id)}`;
export const ask = (item_id: string, question: string) => call<Answer>("/ask", json({ item_id, question }));
export const agentChat = (session_id: string, message: string) => call<AgentReply>("/agent/chat", json({ session_id, message }));
export const createEscrow = async (item_id: string, amount: number, currency = "INR", quote_id?: string) => {
  const mandate = await call<Mandate>("/escrow", json({ item_id, payer: "buyer", amount, currency, quote_id }));
  if (typeof window !== "undefined") window.dispatchEvent(new Event("fw-purchases-updated"));
  return mandate;
};
export type Offer = { status: string; price: number; currency: string; item_id: string;
  quote_id?: string; negotiation_id?: string; round?: number; max_rounds?: number; note?: string };
export const makeOffer = (item_id: string, amount: number, negotiation_id = "") =>
  call<Offer>("/offers", json({ item_id, amount, negotiation_id }));
export const getEscrow = (id: string) => call<Mandate>(`/escrow/${encodeURIComponent(id)}`);
export const getPurchases = () => call<Purchase[]>("/purchases");
export const getSellerDrafts = () => call<SavedListing[]>("/seller/drafts");
export const acceptDelivery = (id: string) => call<Mandate>(`/escrow/${encodeURIComponent(id)}/accept`, json({}));
export const getIssues = (itemId?: string) => call<IssueReport[]>(itemId ? `/issues?item_id=${encodeURIComponent(itemId)}` : "/issues");
export const getIssue = (id: string) => call<IssueReport>(`/issues/${encodeURIComponent(id)}`);
export const submitIssue = (itemId: string, buyerText: string, mandateId: string | null, video?: Blob | null, photos?: File[]) =>
  call<IssueReport>("/issues", { method: "POST", body: form({ item_id: itemId, buyer_text: buyerText, mandate_id: mandateId ?? "" }, video, photos) });
export const addIssueEvidence = (issueId: string, video?: Blob | null, photos?: File[]) =>
  call<IssueReport>(`/issues/${encodeURIComponent(issueId)}/evidence`, { method: "POST", body: form({}, video, photos) });
export const reviewQueue = (token: string) => call<IssueReport[]>("/review", { headers: { Authorization: `Bearer ${token}` } });
export const decideIssue = (id: string, decision: HumanDecision, token: string) =>
  call<IssueReport>(`/issues/${encodeURIComponent(id)}/decision`, { ...json(decision), headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` } });
export const evidenceUrl = (path: string) => `${API_BASE}${path}`;
export const postTake = (code: string, video?: Blob | null, photos?: File[]) =>
  call<ConditionRecord>("/take", { method: "POST", body: form({ code }, video, photos) });

export type SellerIssue = { code: string; region: string; description: string };
export type SellerDraft = { id: string; status: string; revision: number;
  asking_price?: number | null; currency?: string; negotiation_enabled?: boolean;
  answer: "issues_reported" | "none_known" | "unknown" | null; issues: SellerIssue[];
  record: ConditionRecord; limitations: string[]; guidance: string[];
  attempts: { id: string; status: string; created_at: string; error?: string;
    media: { url: string; sha256: string }[] }[]; history: Record<string, unknown>[] };
export const getSellerDraft = (id: string) => call<SellerDraft>(`/seller/drafts/${encodeURIComponent(id)}`);
export const saveSellerDeclarations = (id: string, revision: number, answer: NonNullable<SellerDraft["answer"]>, issues: SellerIssue[]) =>
  call<SellerDraft>(`/seller/drafts/${encodeURIComponent(id)}/declarations`, json({ revision, answer, issues }));
export const addSellerEvidence = (id: string, revision: number, photos: File[], video?: File | null) =>
  call<SellerDraft>(`/seller/drafts/${encodeURIComponent(id)}/evidence`, { method: "POST", body: form({ revision: String(revision) }, video, photos) });
export const publishSellerDraft = (id: string, revision: number, acknowledge_limitations: boolean) =>
  call<SellerDraft>(`/seller/drafts/${encodeURIComponent(id)}/publish`, json({ revision, acknowledge_limitations }));
export const saveSellerPrice = (id: string, revision: number, asking_price: number, negotiation_enabled: boolean, minimum_price?: number) =>
  call<SellerDraft>(`/seller/drafts/${encodeURIComponent(id)}/price`, json({ revision, asking_price, currency: "INR", negotiation_enabled, minimum_price }));

/* ---------- media ---------- */
export const frameUrl = (itemId: string, frameId: string) => `${API_BASE}/media/${encodeURIComponent(itemId)}/${frameId}.jpg`;

/** Findings carry absolute server paths; the media route serves anything under items/<id>/. */
export function cropUrl(itemId: string, serverPath: string | null | undefined): string | null {
  if (!serverPath) return null;
  const p = serverPath.replace(/\\/g, "/");
  const marker = `/items/${itemId}/`;
  const i = p.lastIndexOf(marker);
  if (i === -1) return null;
  const rest = p
    .slice(i + marker.length)
    .split("/")
    .map(encodeURIComponent)
    .join("/");
  return `${API_BASE}/media/${encodeURIComponent(itemId)}/${rest}`;
}

/* ---------- small helpers ---------- */
export const yen = (n: number, cur = "INR") => new Intl.NumberFormat("en-IN", {
  style: "currency", currency: cur, maximumFractionDigits: 0 }).format(n);
export const band = (b: [number, number] | null, cur = "INR") => (b ? b[0] === b[1] ? yen(b[0], cur) : `${yen(b[0], cur)}–${yen(b[1], cur)}` : "No estimate");
export const gradeRange = (g: number[]) =>
  g.length ? (Math.min(...g) === Math.max(...g) ? `Grade ${g[0]} of 5` : `Grade ${Math.min(...g)}–${Math.max(...g)} of 5`) : "Grade not set";
export const words = (s: string) => s.replace(/_/g, " ");
/* Plain-English text for backend enum values (enums themselves are unchanged). */
export const issueStatusText = (s: string) => ({ processing: "We are checking the photos", awaiting_review: "Waiting for a person to check", needs_evidence: "We need one more photo from you", resolved: "Decided" } as Record<string, string>)[s] ?? words(s);
export const paymentStatusText = (s: string) => ({ held: "Simulated payment on hold until you accept delivery or a person checks an issue", released: "Simulated: seller has been paid", refunded: "Simulated: you got your money back", partial: "Simulated: part refund, seller got the rest" } as Record<string, string>)[s] ?? words(s);
export const decisionText = (d: { action: string; refund_pct?: number }, amount?: number | null, cur = "INR") => {
  if (d.action === "release") return "Seller gets paid. The reviewer found the item matches the listing.";
  if (d.action === "request_evidence") return "We need one more photo from you. Payment stays on hold.";
  const pct = d.refund_pct ?? 0;
  if (pct >= 100) return "You get your money back" + (amount != null ? ` (${yen(amount, cur)}, simulated).` : ".");
  if (amount != null) { const back = Math.round(amount * pct / 100); return `Part refund: you get ${yen(back, cur)} back, seller gets ${yen(amount - back, cur)} (simulated).`; }
  return `Part refund: you get ${pct}% back, seller gets the rest.`;
};
export const sentence = (s: string) => { const text = words(s).trim().replace(/([^.!?]) Visual confirmation/g, "$1. Visual confirmation"); return !text || /[.!?。！？]$/.test(text) ? text : `${text}.`; };
export const itemName = (r: { item: ConditionRecord["item"] }) => [r.item.brand, r.item.colour, r.item.type].filter(Boolean).join(" ");

/** Mandate ids are remembered per item so /unbox and /case can find the escrow. */
export const rememberMandate = (itemId: string, m: { id: string; amount: number; currency: string }) => {
  try {
    localStorage.setItem(`fw.mandate.${itemId}`, JSON.stringify({ id: m.id, amount: m.amount, currency: m.currency }));
  } catch {}
};
export const recallMandate = (itemId: string): { id: string; amount: number; currency: string } | null => {
  try {
    const v = localStorage.getItem(`fw.mandate.${itemId}`);
    return v ? JSON.parse(v) : null;
  } catch {
    return null;
  }
};
