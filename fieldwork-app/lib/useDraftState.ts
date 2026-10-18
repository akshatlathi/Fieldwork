"use client";
import { useCallback, useRef, useSyncExternalStore, type Dispatch, type SetStateAction } from "react";
import { createDraftStore } from "./draftStore";

const drafts = createDraftStore(() => typeof window === "undefined" ? undefined : window.sessionStorage);

export const readDraftState = <T,>(key: string, initial: T, persist = true) => drafts.get(key, initial, persist);

/** Setters remain valid while a route is unmounted, so pending requests can finish. */
export function useDraftState<T>(key: string, initial: T, persist = true): [T, Dispatch<SetStateAction<T>>] {
  const initialRef = useRef(initial);
  const subscribe = useCallback((listener: () => void) => drafts.subscribe(key, initialRef.current, listener, persist), [key, persist]);
  const snapshot = useCallback(() => drafts.get(key, initialRef.current, persist), [key, persist]);
  const serverSnapshot = useCallback(() => initialRef.current, []);
  const value = useSyncExternalStore(subscribe, snapshot, serverSnapshot);
  const set = useCallback<Dispatch<SetStateAction<T>>>((next) => drafts.set(key, initialRef.current, next, persist), [key, persist]);
  return [value, set];
}
