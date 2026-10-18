"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { Camera, Circle } from "lucide-react";
import { Button } from "./Button";
import styles from "./Flow.module.css";

type Props = {
  seconds: number;
  /** Called with the finished clip. */
  onRecorded: (clip: Blob) => void;
  /** Shown over the live camera (e.g. the one-time code). */
  overlay?: ReactNode;
  idleText: string;
  recordLabel?: string;
  disabled?: boolean;
};

function pickType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return ["video/webm;codecs=vp9", "video/webm", "video/mp4"].find((t) => MediaRecorder.isTypeSupported(t));
}

/* Rear camera preview + a fixed-length MediaRecorder clip. Needs a secure context (https or localhost). */
export function CameraCapture({ seconds, onRecorded, overlay, idleText, recordLabel = "Record", disabled }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recRef = useRef<MediaRecorder | null>(null);
  const mounted = useRef(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [on, setOn] = useState(false);
  const [left, setLeft] = useState<number | null>(null);
  const [error, setError] = useState("");

  const stop = useCallback(() => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setOn(false);
  }, []);
  useEffect(() => { mounted.current = true; return () => {
    mounted.current = false;
    if (timerRef.current) clearInterval(timerRef.current);
    const recorder = recRef.current;
    // Leaving a route must stop camera access without uploading a partial clip.
    if (recorder) { recorder.onstop = null; if (recorder.state !== "inactive") recorder.stop(); }
    streamRef.current?.getTracks().forEach(track => track.stop());
    streamRef.current = null;
  }; }, []);

  async function start() {
    setError("");
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
      if (!mounted.current) { s.getTracks().forEach(track => track.stop()); return; }
      streamRef.current = s;
      setOn(true);
      requestAnimationFrame(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = s;
          void videoRef.current.play();
        }
      });
    } catch {
      setError("Camera isn't available here. Use photos instead.");
    }
  }

  function record() {
    const s = streamRef.current;
    if (!s) return;
    if (typeof MediaRecorder === "undefined") { setError("Video recording is not supported here. Use the photo or video upload below."); return; }
    const type = pickType();
    const chunks: Blob[] = [];
    let rec: MediaRecorder;
    try { rec = new MediaRecorder(s, type ? { mimeType: type } : undefined); }
    catch { setError("Recording could not start. Use the upload option below."); return; }
    recRef.current = rec;
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = () => {
      setLeft(null);
      stop();
      onRecorded(new Blob(chunks, { type: rec.mimeType || type || "video/webm" }));
    };
    rec.start();
    setLeft(seconds);
    const t0 = Date.now();
    timerRef.current = setInterval(() => {
      const remaining = Math.max(0, seconds - Math.floor((Date.now() - t0) / 1000));
      setLeft(remaining);
      if (remaining <= 0) {
        if (timerRef.current) clearInterval(timerRef.current);
        if (rec.state !== "inactive") rec.stop();
      }
    }, 250);
  }

  return (
    <div className={styles.section}>
      <div className={styles.cam}>
        {on ? <video ref={videoRef} muted playsInline aria-label="Camera preview" /> : <div className={`${styles.camIdle} t-body`}>{idleText}</div>}
        {left !== null && (
          <p className={`${styles.rec} t-meta tnum`} role="timer">
            REC · {left}s
          </p>
        )}
        {on && overlay && <div className={styles.camOverlay}>{overlay}</div>}
      </div>
      {error && <p className={`${styles.err} t-body-s`} role="alert">{error}</p>}
      {!on ? (
        <Button fullWidth disabled={disabled} onClick={start} iconLeading={<Camera size={20} strokeWidth={2} aria-hidden="true" />}>
          Open camera
        </Button>
      ) : (
        <Button fullWidth disabled={disabled || left !== null} onClick={record} iconLeading={<Circle size={20} strokeWidth={2} aria-hidden="true" />}>
          {left !== null ? "Recording…" : `${recordLabel} (${seconds} s)`}
        </Button>
      )}
    </div>
  );
}
