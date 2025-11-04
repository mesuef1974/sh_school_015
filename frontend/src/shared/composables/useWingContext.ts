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
    // Supervisor full name only (لا نستخدم اسم المستخدم username)
    const supFull = me?.staff?.full_name || me?.user?.full_name || "";

    // إذا لم يكن لدى المستخدم صلاحية مشرف جناح وليس سوبر، لا نعرض العبارة
    if (!(isSuper.value || ((me?.roles || []).map((r: any) => String(r).toLowerCase()).some((r: string) => r.includes('wing') && r.includes('supervisor'))))) {
      // ملاحظة: صفحات الواجهة تستخدم hasWingRole/isSuper لإظهار التحذيرات عند الحاجة
      // هنا نعيد نصًا فارغًا لتجنّب عرض معلومات مضللة
      // إبقاء الدالة نقية بدون اعتماد دائري على hasWingRole
      return '';
    }

    // Helper: sanitize name (remove leading 'جناح ' / 'الجناح ')
    const sanitizeName = (s: any) => {
      let name = (s || '').toString().trim();
      if (name) name = name.replace(/^\s*(?:الجناح|جناح)\s+/u, '').trim();
      return name;
    };
    // Remove duplicate wing number from name (e.g., 'الوسيل 5' when number = 5)
    const stripDuplicateNumber = (name: string, numStr: string) => {
      if (!name || !numStr) return name;
      const num = numStr.replace(/\s+/g, '');
      // Patterns at end or wrapped in parentheses or with dashes
      const patterns = [
        new RegExp(`\\s*[\u002D\u2013\u2014]?\\s*\\(?${num}\\)?$`), // ... 5) at end with optional dash/space
        new RegExp(`^\\(?${num}\\)?\\s*[\u002D\u2013\u2014]?\\s*`),   // (5) ... at start
      ];
      let out = name;
      for (const rx of patterns) {
        out = out.replace(rx, '').trim();
      }
      // Also remove standalone duplicate like ' 5 ' in middle surrounded by dashes
      out = out.replace(new RegExp(`\\s*[\u002D\u2013\u2014]?\\s*${num}\\s*[\u002D\u2013\u2014]?\\s*`), ' ').trim();
      return out.replace(/\s{2,}/g, ' ').trim();
    };

    // If a wing is explicitly selected (e.g., timetable), prefer it
    if (selectedWingId.value) {
      let nameStr = sanitizeName(selectedWingName.value);
      const numStr = String(selectedWingId.value || '').trim();
      nameStr = stripDuplicateNumber(nameStr, numStr);
      const parts: string[] = [];
      if (numStr) parts.push(numStr);
      if (nameStr) parts.push(nameStr);
      if (supFull) parts.push(String(supFull));
      if (!parts.length) return '';
      return `جناح ${parts.join(' - ')}`;
    }

    // Default: use primary wing info from backend
    let nameStr = sanitizeName(pw?.name);
    const numStr = (pw?.number != null && pw?.number !== undefined && pw?.number !== 0) ? String(pw.number) : '';
    nameStr = stripDuplicateNumber(nameStr, numStr);
    const parts: string[] = [];
    if (numStr) parts.push(numStr);
    if (nameStr) parts.push(nameStr);
    if (supFull) parts.push(String(supFull));
    if (!parts.length) return '';
    return `جناح ${parts.join(' - ')}`;
  });
  const primaryWing = computed(() => (cached.value?.primary_wing || null));
  const supervisorName = computed(() => (cached.value?.staff?.full_name || cached.value?.user?.full_name || cached.value?.user?.username || null));

  return { ensureLoaded, loading, error, wingLabelFull, primaryWing, supervisorName, me: cached, setSelectedWing, clearSelectedWing, selectedWingId, hasWingRole, isSuper };
}
