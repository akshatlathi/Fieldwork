/** Route-independent state. Binary inputs and active work live in memory;
 * serializable drafts may also survive a reload in this browser tab. */
type StorageLike = Pick<Storage, "getItem" | "setItem">;
type Update<T> = T | ((previous: T) => T);

export function createDraftStore(storage: () => StorageLike | undefined = () => undefined) {
  const entries = new Map<string, { value: unknown; listeners: Set<() => void> }>();
  function entry<T>(key: string, initial: T, persist: boolean) {
    let found = entries.get(key);
    if (!found) {
      let value = initial;
      if (persist) {
        try { const saved = storage()?.getItem(key); if (saved !== null && saved !== undefined) value = JSON.parse(saved); } catch { /* In-memory drafts still work. */ }
      }
      found = { value, listeners: new Set() }; entries.set(key, found);
    }
    return found;
  }
  return {
    get<T>(key: string, initial: T, persist = true): T { return entry(key, initial, persist).value as T; },
    set<T>(key: string, initial: T, update: Update<T>, persist = true) {
      const current = entry(key, initial, persist);
      current.value = typeof update === "function" ? (update as (value: T) => T)(current.value as T) : update;
      if (persist) { try { storage()?.setItem(key, JSON.stringify(current.value)); } catch { /* Storage may be full or disabled. */ } }
      current.listeners.forEach(listener => listener());
    },
    subscribe(key: string, initial: unknown, listener: () => void, persist = true) {
      const current = entry(key, initial, persist); current.listeners.add(listener);
      return () => { current.listeners.delete(listener); };
    },
  };
}
