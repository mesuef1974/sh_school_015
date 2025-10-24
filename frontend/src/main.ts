import { createApp } from 'vue';
import { createPinia } from 'pinia';
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';
import App from './app/App.vue';
import { router } from './app/router';
import './styles/design-system.css';
import './styles/maronia.css';
import './styles/professional-tables.css';
import { VueQueryPlugin, QueryClient, VueQueryPluginOptions } from '@tanstack/vue-query';
import 'vue-toastification/dist/index.css';
import Toast from 'vue-toastification';
// Unified Icon component: wraps Iconify and supports school icons (sc:*)
import AppIcon from './components/ui/Icon.vue';
import Vue3Lottie from 'vue3-lottie';

// PrimeVue imports
import PrimeVue from 'primevue/config';
import 'primeicons/primeicons.css';

// VueUse Motion
import { MotionPlugin } from '@vueuse/motion';

// Vue Sonner (Toast notifications)
import { Toaster } from 'vue-sonner';

const app = createApp(App);

// Pinia with persistedstate plugin
const pinia = createPinia();
pinia.use(piniaPluginPersistedstate);
app.use(pinia);

// Register global components
app.component('Icon', AppIcon);
app.component('Toaster', Toaster);

// PrimeVue setup with RTL support
app.use(PrimeVue, {
  locale: {
    startsWith: 'يبدأ بـ',
    contains: 'يحتوي',
    notContains: 'لا يحتوي',
    endsWith: 'ينتهي بـ',
    equals: 'يساوي',
    notEquals: 'لا يساوي',
    noFilter: 'بدون فلتر',
    filter: 'فلتر',
    lt: 'أقل من',
    lte: 'أقل من أو يساوي',
    gt: 'أكبر من',
    gte: 'أكبر من أو يساوي',
    dateIs: 'التاريخ هو',
    dateIsNot: 'التاريخ ليس',
    dateBefore: 'قبل',
    dateAfter: 'بعد',
    clear: 'مسح',
    apply: 'تطبيق',
    matchAll: 'تطابق الكل',
    matchAny: 'تطابق أي',
    addRule: 'إضافة قاعدة',
    removeRule: 'حذف قاعدة',
    accept: 'نعم',
    reject: 'لا',
    choose: 'اختر',
    upload: 'رفع',
    cancel: 'إلغاء',
    dayNames: ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'],
    dayNamesShort: ['أحد', 'إثنين', 'ثلاثاء', 'أربعاء', 'خميس', 'جمعة', 'سبت'],
    dayNamesMin: ['أح', 'إث', 'ث', 'أر', 'خ', 'ج', 'س'],
    monthNames: ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'],
    monthNamesShort: ['ينا', 'فبر', 'مار', 'أبر', 'ماي', 'يون', 'يول', 'أغس', 'سبت', 'أكت', 'نوف', 'ديس'],
    today: 'اليوم',
    weekHeader: 'أسبوع',
    firstDayOfWeek: 6,
    showMonthAfterYear: false,
    dateFormat: 'dd/mm/yy',
    weak: 'ضعيف',
    medium: 'متوسط',
    strong: 'قوي',
    passwordPrompt: 'أدخل كلمة المرور',
    emptyFilterMessage: 'لا توجد نتائج',
    emptyMessage: 'لا توجد خيارات متاحة'
  }
});

// VueUse Motion (for animations)
app.use(MotionPlugin);

// Vue Query setup (sane defaults for dev)
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, retry: 1, staleTime: 60_000 }
  }
});
app.use(VueQueryPlugin, { queryClient } as VueQueryPluginOptions);

// Toast plugin (Arabic RTL-friendly defaults) - Keep for backward compatibility
app.use(Toast, { rtl: true, position: 'top-center', timeout: 3000 });

// Vue3 Lottie (global component registration)
app.use(Vue3Lottie, { name: 'Vue3Lottie' });

app.use(router);
app.mount('#app');