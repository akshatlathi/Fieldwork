/* Mock data for the first Fieldwork front-end. No backend yet. */

export type EvidenceState =
  | "shown"
  | "not-shown"
  | "differs"
  | "cant-tell"
  | "system"
  | "money"
  | "pending";

export type Claim = {
  id: string;
  title: string;
  support: string;
  state: EvidenceState;
  /** Overrides the default state label, e.g. "Read from screen". */
  stateLabel?: string;
  source?: string;
  photoLabel?: string;
};

export const people = {
  seller: { name: "Priya", city: "Bengaluru" },
  buyer: { name: "Arjun", city: "Pune" },
  reviewer: { name: "Meera", role: "Trust & Safety" },
};

export const item = {
  slug: "iphone-13",
  title: "iPhone 13",
  fullTitle: "iPhone 13, 128 GB, Midnight",
  storage: "128 GB",
  colour: "Midnight",
  battery: 87,
  price: 24999,
  priceLabel: "₹24,999",
  floorLabel: "₹22,500",
  usedFor: "1–2 years",
  photoCount: 6,
  sellerNote: "Used 1–2 years · Never repaired · Box + bill",
};

export const claims: Claim[] = [
  {
    id: "model",
    title: "Model",
    support: "iPhone 13",
    state: "shown",
    source: "Photo 1 · front",
    photoLabel: "[01] FRONT",
  },
  {
    id: "storage",
    title: "Storage",
    support: "128 GB",
    state: "shown",
    source: "Settings screenshot",
    photoLabel: "[06] SETTINGS · ABOUT",
  },
  {
    id: "battery",
    title: "Battery health",
    support: "87%",
    state: "shown",
    stateLabel: "Read from screen",
    source: "Settings screenshot · Battery",
    photoLabel: "[06] SETTINGS · BATTERY",
  },
  {
    id: "screen",
    title: "Screen condition",
    support: "No crack visible in 5 angles",
    state: "shown",
    source: "Photo 4 · back angle and 4 more",
    photoLabel: "[04] SCREEN",
  },
  {
    id: "back-edge",
    title: "Back edge",
    support: "Not shown yet",
    state: "not-shown",
  },
];

export const claimsShown = claims.filter((c) => c.state === "shown").length;
export const claimsTotal = claims.length;

export type NearbyItem = {
  slug: string;
  title: string;
  price: string;
  attrs: string;
  where: string;
  shown: number;
  total: number;
  photoLabel: string;
};

export const nearby: NearbyItem[] = [
  {
    slug: "iphone-13",
    title: "iPhone 13",
    price: "₹24,999",
    attrs: "128 GB · Battery 87%",
    where: "Priya · Bengaluru",
    shown: 4,
    total: 5,
    photoLabel: "[01] FRONT",
  },
  {
    slug: "iphone-12",
    title: "iPhone 12",
    price: "₹18,500",
    attrs: "64 GB · Battery 82%",
    where: "Pune · 3 km",
    shown: 5,
    total: 5,
    photoLabel: "[01] FRONT",
  },
  {
    slug: "galaxy-s21",
    title: "Galaxy S21 FE",
    price: "₹16,200",
    attrs: "128 GB · Battery 90%",
    where: "Pune · 6 km",
    shown: 3,
    total: 5,
    photoLabel: "[01] FRONT",
  },
];

export const listingDraft = {
  title: "iPhone 13, 128 GB, Midnight",
  specs: ["128 GB", "Midnight", "Battery 87%"],
  descriptionEn:
    "iPhone 13 in Midnight, 128 GB. Battery health 87%, read from the Settings screen. No crack visible on the screen in 5 photo angles.",
  descriptionHi:
    "iPhone 13, Midnight रंग, 128 GB। बैटरी हेल्थ 87%, Settings स्क्रीन से पढ़ी गई। 5 एंगल की फ़ोटो में स्क्रीन पर कोई क्रैक नहीं दिखता।",
  usedLineEn: (answer: string) => `Used ${answer}.`,
  usedLineHi: (answer: string) => `${answer} इस्तेमाल किया।`,
};

export const quickQuestions = [
  {
    id: "used",
    label: "How long used?",
    options: ["<1 year", "1–2 years", "2+ years", "Not sure"],
  },
  {
    id: "repairs",
    label: "Any repairs?",
    options: ["Never repaired", "Repaired", "Not sure"],
  },
  {
    id: "box",
    label: "Box and bill?",
    options: ["Box + bill", "Box only", "Neither"],
  },
];

export const pricing = {
  suggestedLow: 23800,
  suggestedHigh: 25500,
  suggestedLabel: "₹23,800 – ₹25,500",
  initial: 24999,
  floor: 22500,
  step: 500,
};

export const priceTimeline = [
  { id: "offer", label: "Offer", amount: "₹22,000", by: "Your agent" },
  { id: "counter", label: "Counter", amount: "₹24,000", by: "Priya's agent" },
  { id: "agreed", label: "Agreed", amount: "₹23,200", by: "Both agents" },
];

export const deal = {
  ceiling: "₹23,500",
  agreed: "₹23,200",
  agreedNumber: 23200,
  margin: "₹300",
  counterparty: "Priya's agent",
};

export type HandoverResult = "matches" | "differs" | "cant-tell";

export const handoverChecks = [
  "Checking with listing…",
  "Comparing photos",
  "Matching serial and marks",
  "Checking condition",
];

export const handoverReport: Claim[] = [
  {
    id: "model",
    title: "Same model",
    support: "iPhone 13, Midnight",
    state: "shown",
    source: "Arrival photo 1 · front",
  },
  {
    id: "serial",
    title: "Serial number",
    support: "Read from the About screen, matches the listing",
    state: "shown",
    stateLabel: "Matches",
    source: "Arrival photo 4 · About screen",
  },
  {
    id: "mark",
    title: "Unit identity marker",
    support: "Edge mark matches the listing photo",
    state: "shown",
    stateLabel: "Matches",
    source: "Arrival photo 3 · edge",
  },
  {
    id: "screen",
    title: "Screen condition",
    support: "No crack visible, same as the listing",
    state: "shown",
    stateLabel: "Matches",
    source: "Arrival photo 2 · screen",
  },
  {
    id: "battery",
    title: "Battery health",
    support: "87%, same as the listing",
    state: "shown",
    stateLabel: "Matches",
    source: "Arrival photo 4 · Battery",
  },
];

export const caseFw = {
  id: "FW-1042",
  slug: "fw-1042",
  intake: [
    {
      id: "where",
      question: "Where on the screen is the crack?",
      options: ["Top left", "Centre", "Along an edge", "Not sure"],
    },
    {
      id: "want",
      question: "What would you like to happen?",
      options: ["Repair credit", "Return the phone", "Not sure yet"],
    },
  ],
  attached: ["Listing photos", "Handover photos", "Chat"],
  answered: [
    { q: "Where is the crack?", a: "Top left of the screen", by: "Arjun" },
    { q: "When did you notice it?", a: "At handover, before payment release", by: "Arjun" },
    { q: "What outcome do you want?", a: "Repair credit", by: "Arjun" },
  ],
  facts: [
    {
      id: "f1",
      text: "Crack visible in arrival photo 2",
      state: "differs" as EvidenceState,
      source: "Arrival photo 2 · screen, top left",
    },
    {
      id: "f2",
      text: "Not visible in listing photo 4",
      state: "shown" as EvidenceState,
      source: "Listing photo 4 · screen",
    },
    {
      id: "f3",
      text: "Not visible in the turn video",
      state: "shown" as EvidenceState,
      source: "Listing turn video · 0:03",
    },
    {
      id: "f4",
      text: "Serial matches",
      state: "shown" as EvidenceState,
      source: "Handover photo 4 · About screen",
    },
  ],
  outcome: {
    saw: "Crack visible in arrival photo 2. Not visible in listing photo 4.",
    rule: "Condition differences reported at handover may qualify for a repair credit.",
    decision: "Repair credit recommended, and confirmed by a person.",
    appeal: "If this looks wrong to you, ask for another review.",
  },
};

export const askExchange = {
  question: "Back mein dent hai?",
  translation: "Is there a dent on the back?",
  answer: "Not shown clearly in the photos.",
  source: "Photo 4 · back angle",
  cropLabel: "[04] BACK · CROP",
};

export const itemHistory = [
  { id: "h1", when: "3 Oct · 10:42", text: "Evidence captured", detail: "5 guided angles, 1 unit identity marker" },
  { id: "h2", when: "3 Oct · 10:43", text: "Settings screen read", detail: "Battery 87%, 128 GB" },
  { id: "h3", when: "3 Oct · 10:44", text: "Listed", detail: "₹24,999 · Priya, Bengaluru" },
  { id: "h4", when: "Now", text: "No open cases", detail: "No problems reported on this item" },
];
