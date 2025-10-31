import { ref, computed } from "vue";
import { getWingMe } from "../api/client";

const cached = ref<any | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
// Selected wing override (set by pages that allow choosing a wing)
const selectedWingId = ref<number | null>(null);
const selectedWingName = ref<string | null>(null);

export function clearWingContext() {
  cached.value = null;
  error.value = null;
  loading.value = false;
  selectedWingId.value = null;
  selectedWingName.value = null;
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
  function setSelectedWing(id: number | null, name?: string | null) {
    selectedWingId.value = id != null ? Number(id) : null;
    selectedWingName.value = (name ?? null) as any;
  }
  function clearSelectedWing() {
    selectedWingId.value = null;
    selectedWingName.value = null;
  }
  const roles = computed(() => (cached.value?.roles ?? []).map((r: any) => String(r || "").trim().toLowerCase()));
  const isSuper = computed(() => Boolean(cached.value?.user?.is_superuser));
  const hasWingRole = computed(() => {
    // Accept common aliases (Arabic/English) for resiliency
    const aliases = ["wing_supervisor", "مشرف الجناح", "مشرف_الجناح", "مشرف جناح", "supervisor_wing"];
    const hasAlias = roles.value.some((r: string) => aliases.includes(r));
    const fuzzy = roles.value.some((r: string) => r.includes("wing") && r.includes("supervisor"));
    return Boolean(isSuper.value || hasAlias || fuzzy);
  });
  const wingLabelFull = computed(() => {
    const me = cached.value || {};
    const pw = me?.primary_wing || null;
    const sup = me?.staff?.full_name || me?.user?.full_name || me?.user?.username || "";

    // If a wing is explicitly selected (e.g., from timetable selector), prefer it for the label.
    if (selectedWingId.value) {
      const parts: string[] = [];
      const nameStrRaw = (selectedWingName.value || "").toString();
      let nameStr = nameStrRaw.trim();
      if (nameStr) nameStr = nameStr.replace(/^\s*(?:الجناح|جناح)\s+/u, "").trim();
      if (nameStr) parts.push(nameStr);
      // Show the ID if we don't have a number; avoid duplicating if already in name
      const idStr = String(selectedWingId.value);
      if (idStr && !nameStr.includes(idStr)) parts.push(idStr);
      // Show supervisor name only if selected wing equals primary wing (we know that supervisor)
      const sameAsPrimary = pw?.id && Number(pw.id) === Number(selectedWingId.value);
      if (sameAsPrimary && sup) parts.push(String(sup));
      if (!parts.length) return "";
      return `مشرف الجناح ${parts.join(" - ")}`;
    }

    // Default: use primary wing info from backend
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

  return { ensureLoaded, loading, error, wingLabelFull, primaryWing, supervisorName, me: cached, setSelectedWing, clearSelectedWing, selectedWingId, hasWingRole, isSuper };
}