"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";
import styles from "./Sheet.module.css";

type Props = {
  /** "modal" overlays with a scrim and traps focus. "dock" sits in the page flow at the bottom. */
  variant?: "modal" | "dock";
  open?: boolean;
  onClose?: () => void;
  title: string;
  /** Hide the visual title but keep it for assistive tech. */
  hideTitle?: boolean;
  tone?: "light" | "dark";
  children: ReactNode;
};

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/* Bottom sheet (DESIGN.md 7, 9): 20px top radius, level-3 elevation, short slide. */
export function Sheet({ variant = "modal", open = true, onClose, title, hideTitle, tone = "light", children }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const titleId = useId();

  useEffect(() => {
    if (variant !== "modal" || !open) return;
    const previous = document.activeElement as HTMLElement | null;
    const node = ref.current;
    node?.focus();

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose?.();
        return;
      }
      if (e.key !== "Tab" || !node) return;
      const els = Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (els.length === 0) return;
      const first = els[0];
      const last = els[els.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previous?.focus?.();
    };
  }, [open, variant, onClose]);

  if (!open) return null;

  const sheet = (
    <div
      ref={ref}
      tabIndex={-1}
      role={variant === "modal" ? "dialog" : "region"}
      aria-modal={variant === "modal" ? true : undefined}
      aria-labelledby={titleId}
      data-on-dark={tone === "dark" || undefined}
      data-on-light={tone === "light" || undefined}
      className={`${styles.sheet} ${variant === "modal" ? styles.modal : styles.dock} ${tone === "dark" ? styles.dark : ""}`}
    >
      <span className={styles.grabber} aria-hidden="true" />
      <h2 id={titleId} className={hideTitle ? "sr-only" : `${styles.title} t-heading-s`}>
        {title}
      </h2>
      {children}
    </div>
  );

  if (variant === "dock") return sheet;

  return (
    <>
      <div className={styles.scrim} onClick={onClose} aria-hidden="true" />
      <div className={styles.frame}>{sheet}</div>
    </>
  );
}
