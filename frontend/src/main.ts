import { createApp } from "vue";
import { createPinia } from "pinia";
import piniaPluginPersistedstate from "pinia-plugin-persistedstate";
import App from "./app/App.vue";
import { router } from "./app/router";
import "./styles/design-system.css";
import { i18n, setDocumentDirByLocale } from "./app/i18n";
import "./styles/maronia.css";
import "./styles/professional-tables.css";
import { VueQueryPlugin, QueryClient, VueQueryPluginOptions } from "@tanstack/vue-query";
import "vue-toastification/dist/index.css";
import Toast from "vue-toastification";
// Unified Icon component: wraps Iconify and supports school icons (sc:*)
import AppIcon from "./components/ui/Icon.vue";
import Vue3Lottie from "vue3-lottie";

// PrimeVue imports
import PrimeVue from "primevue/config";
import "primeicons/primeicons.css";

// VueUse Motion
import { MotionPlugin } from "@vueuse/motion";

// Vue Sonner (Toast notifications)
import { Toaster } from "vue-sonner";

const app = createApp(App);

// Pinia with persistedstate plugin
const pinia = createPinia();
pinia.use(piniaPluginPersistedstate);
app.use(pinia);

// i18n (Arabic default, English fallback)
app.use(i18n);

// Register global components
app.component("Icon", AppIcon);
app.component("Toaster", Toaster);

// PrimeVue setup with dynamic locale switching based on i18n
const primeLocaleAr: any = {
  startsWith: "يبدأ بـ",
  contains: "يحتوي",
  notContains: "لا يحتوي",
  endsWith: "ينتهي بـ",
  equals: "يساوي",
  notEquals: "لا يساوي",
  noFilter: "بدون فلتر",
  filter: "فلتر",
  lt: "أقل من",
  lte: "أقل من أو يساوي",
  gt: "أكبر من",
  gte: "أكبر من أو يساوي",
  dateIs: "التاريخ هو",
  dateIsNot: "التاريخ ليس",
  dateBefore: "قبل",
  dateAfter: "بعد",
  clear: "مسح",
  apply: "تطبيق",
  matchAll: "تطابق الكل",
  matchAny: "تطابق أي",
  addRule: "إضافة قاعدة",
  removeRule: "حذف قاعدة",
  accept: "نعم",
  reject: "لا",
  choose: "اختر",
  upload: "رفع",
  cancel: "إلغاء",
  dayNames: ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"],
  dayNamesShort: ["أحد", "إثنين", "ثلاثاء", "أربعاء", "خميس", "جمعة", "سبت"],
  dayNamesMin: ["أح", "إث", "ث", "أر", "خ", "ج", "س"],
  monthNames: [
    "يناير",
    "فبراير",
    "مارس",
    "أبريل",
    "مايو",
    "يونيو",
    "يوليو",
    "أغسطس",
    "سبتمبر",
    "أكتوبر",
    "نوفمبر",
    "ديسمبر",
  ],
  monthNamesShort: [
    "ينا",
    "فبر",
    "مار",
    "أبر",
    "ماي",
    "يون",
    "يول",
    "أغس",
    "سبت",
    "أكت",
    "نوف",
    "ديس",
  ],
  today: "اليوم",
  weekHeader: "أسبوع",
  firstDayOfWeek: 6,
  showMonthAfterYear: false,
  dateFormat: "dd/mm/yy",
  weak: "ضعيف",
  medium: "متوسط",
  strong: "قوي",
  passwordPrompt: "أدخل كلمة المرور",
  emptyFilterMessage: "لا توجد نتائج",
  emptyMessage: "لا توجد خيارات متاحة",
};

const primeLocaleEn: any = {
  startsWith: "Starts with",
  contains: "Contains",
  notContains: "Not contains",
  endsWith: "Ends with",
  equals: "Equals",
  notEquals: "Not equals",
  noFilter: "No filter",
  filter: "Filter",
  lt: "Less than",
  lte: "Less than or equal to",
  gt: "Greater than",
  gte: "Greater than or equal to",
  dateIs: "Date is",
  dateIsNot: "Date is not",
  dateBefore: "Before",
  dateAfter: "After",
  clear: "Clear",
  apply: "Apply",
  matchAll: "Match all",
  matchAny: "Match any",
  addRule: "Add rule",
  removeRule: "Remove rule",
  accept: "Yes",
  reject: "No",
  choose: "Choose",
  upload: "Upload",
  cancel: "Cancel",
  dayNames: ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
  dayNamesShort: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
  dayNamesMin: ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"],
  monthNames: [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ],
  monthNamesShort: [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ],
  today: "Today",
  weekHeader: "Week",
  firstDayOfWeek: 0,
  showMonthAfterYear: false,
  dateFormat: "mm/dd/yy",
  weak: "Weak",
  medium: "Medium",
  strong: "Strong",
  passwordPrompt: "Enter a password",
  emptyFilterMessage: "No results found",
  emptyMessage: "No available options",
};

app.use(PrimeVue, { locale: primeLocaleAr });

// Watch i18n locale to update PrimeVue locale dynamically
try {
  // @ts-ignore
  const locRef = i18n.global?.locale;
  if (locRef && typeof locRef === "object" && "value" in locRef) {
    // Lazy import watch to avoid adding it to initial graph unnecessarily
    // @ts-ignore
    import("vue").then(({ watch }) => {
      // @ts-ignore
      watch(
        () => i18n.global.locale.value,
        (newLoc: string) => {
          const pv = (app as any).config?.globalProperties?.$primevue;
          if (pv?.config) {
            pv.config.locale = newLoc === "en" ? primeLocaleEn : primeLocaleAr;
          }
        },
        { immediate: true }
      );
    });
  }
} catch {}

// VueUse Motion (for animations)
app.use(MotionPlugin);

// Vue Query setup (sane defaults for dev)
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, retry: 1, staleTime: 60_000 },
  },
});
app.use(VueQueryPlugin, { queryClient } as VueQueryPluginOptions);

// Toast plugin (Arabic RTL-friendly defaults) - Keep for backward compatibility
app.use(Toast, { rtl: true, position: "top-center", timeout: 3000 });

// Vue3 Lottie (global component registration)
app.use(Vue3Lottie, { name: "Vue3Lottie" });

app.use(router);

// Document title i18n: update on startup and when locale changes
try {
  // @ts-ignore
  const t = (k: string) => (i18n.global?.t ? (i18n.global.t(k) as string) : document.title);
  document.title = t("app.name");
  // Watch locale changes to update the title
  // @ts-ignore
  const locRef = i18n.global?.locale;
  if (locRef && typeof locRef === "object" && "value" in locRef) {
    // Lazy import watch to avoid adding it to initial graph unnecessarily
    // @ts-ignore
    import("vue").then(({ watch }) => {
      // @ts-ignore
      watch(
        () => i18n.global.locale.value,
        () => {
          document.title = t("app.name");
        }
      );
    });
  }
} catch {}

// Development-only accessibility checks (axe) — initialize before mount
// Optional: enable by setting VITE_ENABLE_AXE=true and installing @axe-core/vue manually
if (import.meta.env.DEV && String(import.meta.env.VITE_ENABLE_AXE).toLowerCase() === "true") {
  try {
    // Prevent Vite from trying to pre-resolve this optional dependency when it's not installed
    const spec = "@axe-core/vue";
    // @ts-ignore
    const { default: VueAxe } = await import(/* @vite-ignore */ spec);
    // @ts-ignore - plugin typing may not be available
    app.use(VueAxe, { config: { reporter: "v2" } });
    // You can open the browser console to see violations while navigating in dev
  } catch (e) {
    // Fallback path: load axe-core directly from a public CDN (dev-only) and run checks
    try {
      await new Promise<void>((resolve, reject) => {
        const s = document.createElement("script");
        s.src = "https://unpkg.com/axe-core@4.9.1/axe.min.js";
        s.async = true;
        s.onload = () => resolve();
        s.onerror = () => reject(new Error("Failed to load axe-core from CDN"));
        document.head.appendChild(s);
      });
      const runAxe = async () => {
        // @ts-ignore
        const axe = (window as any).axe;
        if (axe && document?.body) {
          try {
            const results = await axe.run(document.body, { resultTypes: ["violations"] });
            const violations = results?.violations || [];
            const serious = violations.filter((v: any) =>
              ["serious", "critical"].includes(v.impact)
            );
            if (violations.length) {
              console.groupCollapsed(
                "[axe] violations:",
                violations.length,
                "serious/critical:",
                serious.length
              );
              for (const v of violations) console.warn(v);
              console.groupEnd();
              const strict =
                String(import.meta.env.VITE_AXE_STRICT || "false").toLowerCase() === "true";
              if (strict && serious.length) {
                throw new Error("[axe] serious/critical violations present (VITE_AXE_STRICT=true)");
              }
            } else {
              console.info("[axe] no violations found");
            }
          } catch (err) {
            console.warn("[axe] run failed:", err);
          }
        }
      };
      // Run once app/router are ready, then on each route change
      try {
        await router.isReady();
      } catch {}
      runAxe();
      router.afterEach(() => setTimeout(runAxe, 0));
    } catch (cdnErr) {
      console.warn(
        "[@axe-core/vue] not installed and CDN fallback failed (dev-only, optional):",
        cdnErr
      );
    }
  }
}

app.mount("#app");
