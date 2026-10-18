"use client";

import styles from "./Segmented.module.css";

type Option = { id: string; label: string; lang?: string };

type Props = {
  options: Option[];
  value: string;
  onChange: (id: string) => void;
  label: string;
};

/* Two or three mutually exclusive options (e.g. English / Hindi). Selected = fill + weight + aria-pressed. */
export function Segmented({ options, value, onChange, label }: Props) {
  return (
    <div role="group" aria-label={label} className={styles.group}>
      {options.map((o) => {
        const selected = o.id === value;
        return (
          <button
            key={o.id}
            type="button"
            lang={o.lang}
            aria-pressed={selected}
            className={`${styles.option} ${selected ? styles.selected : ""} t-body-s ${o.lang === "hi" ? "t-devanagari" : ""}`}
            onClick={() => onChange(o.id)}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
