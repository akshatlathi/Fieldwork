"use client";

import { useRef, type KeyboardEvent } from "react";
import styles from "./Tabs.module.css";

export type TabDef = { id: string; label: string };

type Props = {
  tabs: TabDef[];
  value: string;
  onChange: (id: string) => void;
  idPrefix: string;
  label: string;
};

export const tabId = (prefix: string, id: string) => `${prefix}-tab-${id}`;
export const panelId = (prefix: string, id: string) => `${prefix}-panel-${id}`;

/* Underline tabs with roving focus and arrow-key navigation. The active tab is marked by weight and an underline. */
export function Tabs({ tabs, value, onChange, idPrefix, label }: Props) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function onKeyDown(e: KeyboardEvent<HTMLButtonElement>, i: number) {
    let next = i;
    if (e.key === "ArrowRight") next = (i + 1) % tabs.length;
    else if (e.key === "ArrowLeft") next = (i - 1 + tabs.length) % tabs.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = tabs.length - 1;
    else return;
    e.preventDefault();
    onChange(tabs[next].id);
    refs.current[next]?.focus();
  }

  return (
    <div role="tablist" aria-label={label} className={styles.list}>
      {tabs.map((t, i) => {
        const selected = t.id === value;
        return (
          <button
            key={t.id}
            ref={(el) => {
              refs.current[i] = el;
            }}
            id={tabId(idPrefix, t.id)}
            role="tab"
            type="button"
            aria-selected={selected}
            aria-controls={panelId(idPrefix, t.id)}
            tabIndex={selected ? 0 : -1}
            className={`${styles.tab} ${selected ? styles.selected : ""} t-body-s`}
            onClick={() => onChange(t.id)}
            onKeyDown={(e) => onKeyDown(e, i)}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}
