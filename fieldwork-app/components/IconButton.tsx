import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import styles from "./IconButton.module.css";

type Common = {
  label: string; // accessible name, required
  children: ReactNode;
  onDark?: boolean;
  glass?: boolean;
};

type AsButton = Common & Omit<ButtonHTMLAttributes<HTMLButtonElement>, "aria-label" | "children"> & { href?: undefined };
type AsLink = Common & { href: string };

export function IconButton(props: AsButton | AsLink) {
  const { label, children, onDark, glass } = props;
  const cls = [styles.iconButton, onDark ? styles.onDark : "", glass ? styles.glass : ""].filter(Boolean).join(" ");
  if (props.href !== undefined) {
    return (
      <Link href={props.href} className={cls} aria-label={label}>
        {children}
      </Link>
    );
  }
  const { label: _l, children: _c, onDark: _o, glass: _g, href: _h, type, ...rest } = props as AsButton;
  void [_l, _c, _o, _g, _h];
  return (
    <button {...rest} type={type ?? "button"} className={cls} aria-label={label}>
      {children}
    </button>
  );
}
