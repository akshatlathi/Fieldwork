import {
  ArrowRightLeft,
  CircleCheck,
  CircleHelp,
  CircleMinus,
  Clock,
  IndianRupee,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";
import type { EvidenceState } from "@/lib/mock";

export type StateMeta = {
  label: string;
  Icon: LucideIcon;
  fg: string;
  bg: string;
  border: string;
};

/* One mapping, so a state always has the same icon, words and colours (DESIGN.md 4.3, 20). */
export const stateMeta: Record<EvidenceState, StateMeta> = {
  shown: {
    label: "Shown",
    Icon: CircleCheck,
    fg: "var(--fw-match-fg)",
    bg: "var(--fw-match-bg)",
    border: "var(--fw-match-border)",
  },
  "not-shown": {
    label: "Not shown yet",
    Icon: CircleMinus,
    fg: "var(--fw-not-shown-fg)",
    bg: "var(--fw-not-shown-bg)",
    border: "var(--fw-not-shown-border)",
  },
  differs: {
    label: "Differs",
    Icon: ArrowRightLeft,
    fg: "var(--fw-differs-fg)",
    bg: "var(--fw-differs-bg)",
    border: "var(--fw-differs-border)",
  },
  "cant-tell": {
    label: "Can't tell",
    Icon: CircleHelp,
    fg: "var(--fw-cant-tell-fg)",
    bg: "var(--fw-cant-tell-bg)",
    border: "var(--fw-cant-tell-border)",
  },
  system: {
    label: "System issue",
    Icon: TriangleAlert,
    fg: "var(--fw-system-fg)",
    bg: "var(--fw-system-bg)",
    border: "var(--fw-system-border)",
  },
  money: {
    label: "Price",
    Icon: IndianRupee,
    fg: "var(--fw-money-fg)",
    bg: "var(--fw-money-bg)",
    border: "var(--fw-money-border)",
  },
  pending: {
    label: "Awaiting review",
    Icon: Clock,
    fg: "var(--fw-not-shown-fg)",
    bg: "var(--fw-not-shown-bg)",
    border: "var(--fw-not-shown-border)",
  },
};
