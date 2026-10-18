import { Fragment } from "react";
import styles from "./Flow.module.css";

// A small safe subset for model text: React escapes all text; no raw HTML.
function inline(text: string) {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^\s)]+\))/g).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={i}>{part.slice(1, -1)}</code>;
    const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (link && /^(https?:\/\/|\/(?!\/))/.test(link[2])) return <a key={i} href={link[2]}>{link[1]}</a>;
    return <Fragment key={i}>{part}</Fragment>;
  });
}

export function FormattedText({ text }: { text: string }) {
  return <div className={styles.formatted}>{text.split(/\n\s*\n/).filter(Boolean).map((block, i) => {
    const lines = block.trim().split("\n");
    if (lines.every(line => /^\s*[-*]\s/.test(line))) return <ul key={i}>{lines.map((line, j) => <li key={j}>{inline(line.replace(/^\s*[-*]\s+/, ""))}</li>)}</ul>;
    if (lines.every(line => /^\s*\d+[.)]\s/.test(line))) return <ol key={i}>{lines.map((line, j) => <li key={j}>{inline(line.replace(/^\s*\d+[.)]\s+/, ""))}</li>)}</ol>;
    return <p key={i}>{lines.map((line, j) => <Fragment key={j}>{j > 0 && <br />}{inline(line.replace(/^#{1,6}\s+/, ""))}</Fragment>)}</p>;
  })}</div>;
}
