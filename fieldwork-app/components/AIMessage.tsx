import type { ReactNode } from "react";
import styles from "./AIMessage.module.css";
import { FormattedText } from "./FormattedText";

type Props = {
  /** Who is speaking. AI messages are always labelled. */
  from: "ai" | "you";
  children: ReactNode;
  /** Optional controls under the message, e.g. quick-answer chips. */
  controls?: ReactNode;
};

/*
  A short, labelled message in an object-specific assistant (DESIGN.md 23).
  Not a chat bubble: a left rail, a label and one or two lines.
*/
export function AIMessage({ from, children, controls }: Props) {
  return (
    <div className={`${styles.root} ${from === "you" ? styles.you : ""}`}>
      <p className={`${styles.who} t-overline`}>
        {from === "ai" ? (
          <>
            <span className={`${styles.ai} t-meta`}>AI</span> Fieldwork
          </>
        ) : (
          "You"
        )}
      </p>
      <div className={`${styles.text} t-body`}>{typeof children === "string" ? <FormattedText text={children} /> : children}</div>
      {controls && <div className={styles.controls}>{controls}</div>}
    </div>
  );
}
