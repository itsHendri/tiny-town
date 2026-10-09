// Opening and saving files, and the autosave in this browser.

// Saves a Blob. Tries the browser's Save dialog, then a page's own download permission (inside claude.ai,
// which only accepts some file types, so `fallbackName` is used there), then a plain download link.
// Resolves "saved", "cancelled" or throws with a readable message.
export async function saveFile(blob, name, { fallbackName, types } = {}) {
  if (window.showSaveFilePicker && window.self === window.top) {
    try {
      const handle = await window.showSaveFilePicker({ suggestedName: name, types });
      const w = await handle.createWritable();
      await w.write(blob);
      await w.close();
      return "saved";
    } catch (e) {
      if (e.name === "AbortError") return "cancelled";
    }
  }
  const downloads = window.claude?.use ? await window.claude.use("downloads").catch(() => null) : null;
  if (downloads) {
    try {
      await downloads.save({ filename: fallbackName || name, data: blob });
      return "saved";
    } catch (e) {
      if (e?.code === "declined") return "cancelled";
      throw new Error(e?.message || "This view can't save files.");
    }
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  return "saved";
}

// Asks for a file and resolves { name, text }, or null if nothing was picked.
export function openFile(accept) {
  return new Promise((resolve) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = accept;
    input.addEventListener("change", async () => {
      const f = input.files?.[0];
      resolve(f ? { name: f.name, text: await f.text() } : null);
    });
    input.addEventListener("cancel", () => resolve(null));
    input.click();
  });
}

const KEY = "tiny-town/autosave";

export function loadAutosave() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

export function writeAutosave(name, text) {
  try { localStorage.setItem(KEY, JSON.stringify({ name, text, at: new Date().toISOString() })); return true; } catch { return false; }
}

export function clearAutosave() {
  try { localStorage.removeItem(KEY); } catch { /* nothing to clear */ }
}
