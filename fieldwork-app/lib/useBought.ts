"use client";
import { useEffect, useState } from "react";
import { recallMandate } from "./api";

/** This browser's own purchase of an item (from local mandates), or null. Client-only. */
export function useBought(itemId: string): { id: string; href: string } | null {
  const [m, setM] = useState<string | null>(null);
  useEffect(() => { setM(recallMandate(itemId)?.id ?? null); }, [itemId]);
  return m ? { id: m, href: `/unbox/${encodeURIComponent(itemId)}?m=${encodeURIComponent(m)}` } : null;
}
