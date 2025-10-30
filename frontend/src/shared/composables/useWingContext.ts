import { ref, computed } from "vue";
import { getWingMe } from "../api/client";

const cached = ref<any | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);

export function clearWingContext() {
  cached.value = null;
  error.value = null;
  loading.value = false;
}

export function useWingContext() {
  // Always fetch fresh data for the current authenticated user to avoid cross-user/wing leakage
  async function ensureLoaded() {
    if (loading.value) return;
    loading.value = true;
    try {
      const me = await getWingMe();
      cached.value = me;
      error.value = null;
    } catch (e: any) {
      try {
        error.value = e?.response?.data?.detail || e?.message || "";
      } catch {
        error.value = "";
      }
    } finally {
      loading.value = false;
    }
  }
  const wingLabelFull = computed(() => {
    const me = cached.value || {};
    const pw = me?.primary_wing || null;
    const sup = me?.staff?.full_name || me?.user?.full_name || me?.user?.username || "";
    // Build: مشرف الجناح <اسم الجناح> - <رقم الجناح> - <اسم مشرف الجناح>
    const parts: string[] = [];
    let nameStr = pw?.name ? String(pw.name) : "";
    // Sanitize wing name: remove leading 'جناح ' or 'الجناح '
    if (nameStr) {
      const trimmed = nameStr.trim();
      nameStr = trimmed.replace(/^\s*(?:الجناح|جناح)\s+/u, "").trim();
    }
    const numStr = pw?.number != null && pw?.number !== undefined && pw.number !== 0 ? String(pw.number) : "";
    if (nameStr) parts.push(nameStr);
    // Avoid duplicating the number if it already exists in the (sanitized) name string
    if (numStr && !nameStr.includes(numStr)) parts.push(numStr);
    if (sup) parts.push(String(sup));
    if (!parts.length) return "";
    return `مشرف الجناح ${parts.join(" - ")}`;
  });
  const primaryWing = computed(() => (cached.value?.primary_wing || null));
  const supervisorName = computed(() => (cached.value?.staff?.full_name || cached.value?.user?.full_name || cached.value?.user?.username || null));

  return { ensureLoaded, loading, error, wingLabelFull, primaryWing, supervisorName, me: cached };
}
