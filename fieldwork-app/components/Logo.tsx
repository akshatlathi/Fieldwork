type Props = {
  size?: number;
  /** Monochrome: a single colour, locator dot included. */
  monochrome?: boolean;
  className?: string;
  title?: string;
};

/* Modular "F": a stem, two arms and a small locator dot. Reads at 16px, works on Paper and Deep Forest. */
export function Logo({ size = 24, monochrome = false, className, title }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      className={className}
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
      fill="currentColor"
    >
      <rect x="4" y="3" width="5" height="18" rx="1" />
      <rect x="10" y="3" width="10" height="5" rx="1" />
      <rect x="10" y="11" width="6" height="4" rx="1" />
      <circle cx="18.25" cy="18.25" r="1.75" fill={monochrome ? "currentColor" : "var(--fw-brand-oxide)"} />
    </svg>
  );
}

export function Wordmark({ size = 24 }: { size?: number }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "var(--fw-space-2)",
        color: "inherit",
      }}
    >
      <span
        style={{
          fontWeight: 400,
          fontFamily: "Georgia, serif",
          fontSize: size,
          lineHeight: "var(--fw-lh-heading-s)",
          letterSpacing: "-0.055em",
        }}
      >
        fieldwork
      </span>
    </span>
  );
}
