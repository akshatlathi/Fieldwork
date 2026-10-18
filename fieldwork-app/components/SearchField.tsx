"use client";

import { Search } from "lucide-react";
import { useId } from "react";
import styles from "./SearchField.module.css";

type Props = {
  label?: string;
  placeholder?: string;
};

/* The label is real (screen-reader text); the placeholder is only a hint, never the label. */
export function SearchField({ label = "Search phones", placeholder = "Search iPhone, Galaxy, Pixel…" }: Props) {
  const id = useId();
  return (
    <form role="search" className={styles.form} onSubmit={(e) => e.preventDefault()}>
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <Search size={20} strokeWidth={2} className={styles.icon} aria-hidden="true" />
      <input id={id} type="search" name="q" placeholder={placeholder} className={`${styles.input} t-body`} autoComplete="off" />
    </form>
  );
}
