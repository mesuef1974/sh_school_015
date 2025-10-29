// Lightweight i18n scaffolding (Phase 2 prep) — not wired yet
// Usage (later):
//   import { i18n } from './app/i18n'
//   app.use(i18n)
// Direction (dir) switching can be handled in a small helper below.

import { createI18n } from "vue-i18n";

export type SupportedLocale = "ar" | "en";

const STORAGE_KEY = "locale";
const envDefault = (import.meta.env.VITE_DEFAULT_LOCALE as SupportedLocale) || "ar";
const fallbackLocale = (import.meta.env.VITE_FALLBACK_LOCALE as SupportedLocale) || "en";

function detectInitialLocale(): SupportedLocale {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem(STORAGE_KEY) as SupportedLocale | null;
    if (stored === "ar" || stored === "en") return stored;
    const nav = navigator.language || (navigator as any).userLanguage || "";
    if (nav.toLowerCase().startsWith("ar")) return "ar";
    if (nav.toLowerCase().startsWith("en")) return "en";
  }
  return envDefault;
}

const initialLocale: SupportedLocale = detectInitialLocale();

const messages = {
  ar: {
    app: {
      name: import.meta.env.VITE_APP_NAME || "منصة المدرسة",
    },
    common: {
      save: "حفظ",
      cancel: "إلغاء",
      close: "إغلاق",
      loading: "جاري التحميل...",
    },
  },
  en: {
    app: {
      name: import.meta.env.VITE_APP_NAME || "School Platform",
    },
    common: {
      save: "Save",
      cancel: "Cancel",
      close: "Close",
      loading: "Loading...",
    },
  },
};

export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: initialLocale,
  fallbackLocale,
  messages,
});

export function setDocumentDirByLocale(locale: SupportedLocale) {
  const rtlLocales = new Set<SupportedLocale>(["ar"]);
  const isRTL = rtlLocales.has(locale);
  document.documentElement.setAttribute("dir", isRTL ? "rtl" : "ltr");
  document.documentElement.lang = locale;
}

export function setLocale(locale: SupportedLocale) {
  if (locale !== "ar" && locale !== "en") return;
  // Update vue-i18n current locale (composition API uses Ref)
  // @ts-ignore
  i18n.global.locale.value = locale;
  try {
    localStorage.setItem(STORAGE_KEY, locale);
  } catch {}
  if (typeof document !== "undefined") setDocumentDirByLocale(locale);
}

// Initialize dir based on initial locale
if (typeof document !== "undefined") {
  setDocumentDirByLocale(initialLocale);
}
