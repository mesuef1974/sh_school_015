import { ref } from "vue";

// Base URL for school (local) icons
const ICON_BASE = (import.meta as any).env?.VITE_BACKEND_ORIGIN
  ? `${(import.meta as any).env.VITE_BACKEND_ORIGIN}/data/icons`
  : "https://127.0.0.1:8443/data/icons";

const manifest = ref<Record<string, { v?: string | number }>>({});
const ready = ref(false);
const LS_MANIFEST = "sc_icons_manifest_v1";

async function loadManifest() {
  if (ready.value) return;
  try {
    const cached = localStorage.getItem(LS_MANIFEST);
    if (cached) {
      manifest.value = JSON.parse(cached);
      ready.value = true;
    }
  } catch {}
  try {
    const res = await fetch(`${ICON_BASE}/manifest.json`, { credentials: "include" });
    if (res.ok) {
      const data = await res.json();
      manifest.value = data || {};
      try {
        localStorage.setItem(LS_MANIFEST, JSON.stringify(manifest.value));
      } catch {}
      ready.value = true;
    }
  } catch {}
}

function cacheKey(name: string) {
  const v = manifest.value?.[name]?.v ?? "0";
  return `sc_icon_${name}_v_${v}`;
}

export async function getSchoolIconSvg(name: string): Promise<string | null> {
  await loadManifest();
  const key = cacheKey(name);
  try {
    const fromLs = localStorage.getItem(key);
    if (fromLs) return fromLs;
  } catch {}

  // Direct fetch fallback even without manifest
  const url = `${ICON_BASE}/${encodeURIComponent(name)}.svg`;
  try {
    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) return null;
    const svg = await res.text();
    // Normalize to currentColor if not explicitly none/currentColor
    const normalized = svg
      .replace(/fill=\"(?!none|currentColor)[^\"]*\"/g, 'fill="currentColor"')
      .replace(/stroke=\"(?!none|currentColor)[^\"]*\"/g, 'stroke="currentColor"');
    try {
      localStorage.setItem(key, normalized);
    } catch {}
    return normalized;
  } catch {
    return null;
  }
}

export async function ensureIconsReady() {
  await loadManifest();
}
