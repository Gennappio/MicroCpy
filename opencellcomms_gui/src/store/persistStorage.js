/**
 * Storage backend for the workflow store's `persist` middleware.
 *
 * The GUI keeps the project being edited in memory only, so any page reload
 * (Vite dev-server reconnect, browser tab discard, F5) used to empty the canvas
 * while the simulation kept running in the backend. This backend keeps a
 * snapshot of the project in localStorage so it comes back after a reload.
 *
 * Two behaviours on top of plain localStorage:
 *  - Writes are coalesced. The canvas pushes every drag frame into the store,
 *    and each snapshot serializes the whole workflow (~100 KB), so the snapshot
 *    is serialized and written at most once per WRITE_DELAY_MS, and immediately
 *    when the tab is hidden or unloaded — the moments a reload can happen.
 *  - It never throws. A missing, full, or corrupt localStorage (quota, Safari
 *    private mode) degrades to "not persisted" with one console warning instead
 *    of breaking every store update.
 */

const WRITE_DELAY_MS = 300;

let pending = null; // { key, value } waiting to be written
let timer = null;
let warned = false;

const warnOnce = (err) => {
  if (warned) return;
  warned = true;
  console.warn('[store] Workflow persistence unavailable — edits will not survive a reload:', err);
};

const flush = () => {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
  if (!pending) return;
  const { key, value } = pending;
  pending = null;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch (err) {
    warnOnce(err);
  }
};

if (typeof window !== 'undefined') {
  window.addEventListener('pagehide', flush);
}
if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flush();
  });
}

// Implements zustand's PersistStorage: values are the middleware's
// `{ state, version }` objects; (de)serialization happens here.
export const workflowPersistStorage = {
  getItem: (key) => {
    try {
      const raw = window.localStorage.getItem(key);
      return raw ? JSON.parse(raw) : null;
    } catch (err) {
      warnOnce(err);
      return null;
    }
  },
  setItem: (key, value) => {
    pending = { key, value };
    if (!timer) timer = setTimeout(flush, WRITE_DELAY_MS);
  },
  removeItem: (key) => {
    pending = null;
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
    try {
      window.localStorage.removeItem(key);
    } catch (err) {
      warnOnce(err);
    }
  },
};
