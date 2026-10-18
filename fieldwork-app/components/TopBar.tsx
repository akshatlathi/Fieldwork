import type { ReactNode } from "react";
import { ChevronLeft } from "lucide-react";
import { IconButton } from "./IconButton";
import { Wordmark } from "./Logo";
import styles from "./TopBar.module.css";

type Props = {
  /** "brand" shows the Fieldwork wordmark. "page" shows a back button and a title. */
  variant?: "brand" | "page";
  title?: string;
  backHref?: string;
  backLabel?: string;
  trailing?: ReactNode;
  onDark?: boolean;
  /** Render the title as a paragraph when the page has its own h1, so there is one h1 per page. */
  titleAs?: "h1" | "p";
};

export function TopBar({ variant = "page", title, backHref = "/", backLabel = "Back", trailing, onDark = false, titleAs = "h1" }: Props) {
  const Title = titleAs;
  return (
    <header className={`${styles.bar} ${onDark ? styles.onDark : ""}`} data-on-dark={onDark || undefined}>
      {variant === "page" ? (
        <>
          <IconButton href={backHref} label={backLabel} onDark={onDark}>
            <ChevronLeft size={24} strokeWidth={2} aria-hidden="true" />
          </IconButton>
          {title && <Title className={`${styles.title} t-heading-s`}>{title}</Title>}
        </>
      ) : (
        <div className={styles.brand}>
          <Wordmark size={24} />
        </div>
      )}
      <div className={styles.trailing}>{trailing}</div>
    </header>
  );
}
