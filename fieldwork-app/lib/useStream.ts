"use client";

import { useEffect, useState } from "react";

/*
  Reveals text progressively (DESIGN.md 34: listing text progressively appearing).
  Reduced motion: shows the full text at once.
*/
export function useStream(text: string, enabled = true, charsPerTick = 3, tickMs = 28) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    const reduce = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setCount(text.length);
      return;
    }
    const id = setInterval(() => {
      setCount((c) => {
        if (c >= text.length) {
          clearInterval(id);
          return c;
        }
        return Math.min(text.length, c + charsPerTick);
      });
    }, tickMs);
    return () => clearInterval(id);
  }, [text, enabled, charsPerTick, tickMs]);

  return { text: text.slice(0, count), done: count >= text.length };
}
