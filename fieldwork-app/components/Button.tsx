import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "secondary" | "tertiary" | "destructive";

type CommonProps = {
  variant?: ButtonVariant;
  size?: "lg" | "md";
  fullWidth?: boolean;
  /** Inverse colours for use on Deep Forest or camera surfaces. */
  onDark?: boolean;
  iconLeading?: ReactNode;
  iconTrailing?: ReactNode;
  loading?: boolean;
  children: ReactNode;
};

type ButtonAsButton = CommonProps &
  Omit<ButtonHTMLAttributes<HTMLButtonElement>, keyof CommonProps> & { href?: undefined };

type ButtonAsLink = CommonProps & {
  href: string;
  disabled?: boolean;
  className?: string;
  "aria-label"?: string;
  onClick?: () => void;
};

export type ButtonProps = ButtonAsButton | ButtonAsLink;

export function Button(props: ButtonProps) {
  const {
    variant = "primary",
    size = "lg",
    fullWidth = false,
    onDark = false,
    iconLeading,
    iconTrailing,
    loading = false,
    children,
  } = props;

  const cls = [
    styles.button,
    "t-button",
    styles[variant],
    styles[size],
    fullWidth ? styles.full : "",
    onDark ? styles.onDark : "",
    loading ? styles.loading : "",
    props.className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  const inner = (
    <>
      {loading ? <span className={styles.spinner} aria-hidden="true" /> : iconLeading}
      <span>{children}</span>
      {!loading && iconTrailing}
    </>
  );

  if ("href" in props && props.href !== undefined) {
    return (
      <Link
        href={props.href}
        className={cls}
        aria-disabled={props.disabled || undefined}
        aria-label={props["aria-label"]}
        tabIndex={props.disabled ? -1 : undefined}
        onClick={props.onClick}
        data-variant={variant}
      >
        {inner}
      </Link>
    );
  }

  const {
    variant: _v,
    size: _s,
    fullWidth: _f,
    onDark: _o,
    iconLeading: _il,
    iconTrailing: _it,
    loading: _l,
    children: _c,
    className: _cn,
    type,
    disabled,
    ...rest
  } = props as ButtonAsButton;
  void [_v, _s, _f, _o, _il, _it, _l, _c, _cn];

  return (
    <button
      {...rest}
      type={type ?? "button"}
      className={cls}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      data-variant={variant}
    >
      {inner}
    </button>
  );
}
