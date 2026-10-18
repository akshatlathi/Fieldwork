import type { KeyboardEvent, ReactNode } from "react";
import styles from "./Chip.module.css";

type Props = {
  children: ReactNode;
  /** "attribute" is static metadata. "answer" is an interactive quick answer. */
  variant?: "attribute" | "answer";
  selected?: boolean;
  onClick?: () => void;
  icon?: ReactNode;
  disabled?: boolean;
  /** Radio semantics for quick-answer groups. */
  role?: "radio";
};

export function Chip({ children, variant = "attribute", selected = false, onClick, icon, disabled, role }: Props) {
  if (variant === "attribute") {
    return (
      <span className={`${styles.chip} ${styles.attribute} t-label`}>
        {icon}
        {children}
      </span>
    );
  }
  return (
    <button
      type="button"
      className={`${styles.chip} ${styles.answer} t-body-s ${selected ? styles.selected : ""}`}
      onClick={onClick}
      disabled={disabled}
      role={role}
      aria-checked={role === "radio" ? selected : undefined}
      aria-pressed={role === "radio" ? undefined : selected}
    >
      {selected && <span className={styles.tick} aria-hidden="true" />}
      {icon}
      {children}
    </button>
  );
}

/** Arrow-key behaviour for a radiogroup of chips: move focus to the next or previous option and select it. */
export function onRadioGroupKeyDown(e: KeyboardEvent<HTMLElement>) {
  const forward = e.key === "ArrowRight" || e.key === "ArrowDown";
  const back = e.key === "ArrowLeft" || e.key === "ArrowUp";
  if (!forward && !back) return;
  const radios = Array.from(e.currentTarget.querySelectorAll<HTMLButtonElement>('[role="radio"]:not(:disabled)'));
  const at = radios.indexOf(document.activeElement as HTMLButtonElement);
  if (at === -1) return;
  e.preventDefault();
  const next = radios[(at + (forward ? 1 : -1) + radios.length) % radios.length];
  next.focus();
  next.click();
}

/** Group wrapper for quick answers: label + radio group. */
export function ChipGroup({ label, children }: { label: string; children: ReactNode }) {
  const id = `chips-${label.replace(/\W+/g, "-").toLowerCase()}`;
  return (
    <div className={styles.group}>
      <p id={id} className="t-label">
        {label}
      </p>
      <div role="radiogroup" aria-labelledby={id} className={styles.row} onKeyDown={onRadioGroupKeyDown}>
        {children}
      </div>
    </div>
  );
}
