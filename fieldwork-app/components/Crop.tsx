"use client";

import { useState } from "react";
import { frameUrl, type Box } from "@/lib/api";
import { PhotoFrame } from "./PhotoFrame";
import styles from "./Flow.module.css";

/* Evidence crop: the boxed region of one evidence frame, cut client-side. Falls back to a quiet frame when no image exists (fixtures). */
export function Crop({ itemId, box, label }: { itemId: string; box: Box; label?: string }) {
  const [dim, setDim] = useState<{ w: number; h: number } | null>(null);
  const [failed, setFailed] = useState(false);
  const src = frameUrl(itemId, box.frame_id);
  const [y0, x0, y1, x1] = box.box_2d;
  const bw = Math.min(1, Math.max(1, x1 - x0) / 1000);
  const bh = Math.min(1, Math.max(1, y1 - y0) / 1000);
  const px = bw >= 1 ? 0 : (x0 / 1000 / (1 - bw)) * 100;
  const py = bh >= 1 ? 0 : (y0 / 1000 / (1 - bh)) * 100;

  if (failed) return <PhotoFrame ratio="4/3" radius="card" compact label={label ?? box.frame_id} />;
  return (
    <>
      {!dim && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt=""
          hidden
          onLoad={(e) => setDim({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
          onError={() => setFailed(true)}
        />
      )}
      {dim && (
        <div
          className={styles.crop}
          role="img"
          aria-label={`Evidence crop${label ? `: ${label}` : ""}`}
          style={{
            aspectRatio: `${bw * dim.w} / ${bh * dim.h}`,
            backgroundImage: `url(${src})`,
            backgroundSize: `${100 / bw}% ${100 / bh}%`,
            backgroundPosition: `${px}% ${py}%`,
          }}
        >
          {label && <span className="t-meta">{label}</span>}
        </div>
      )}
    </>
  );
}
