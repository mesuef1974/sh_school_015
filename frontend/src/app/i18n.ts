// Lightweight i18n scaffolding (Phase 2 prep) — not wired yet
// Usage (later):
//   import { i18n } from './app/i18n'
//   app.use(i18n)
// Direction (dir) switching can be handled in a small helper below.

import { createI18n } from 'vue-i18n'

export type SupportedLocale = 'ar' | 'en'

const defaultLocale = (import.meta.env.VITE_DEFAULT_LOCALE as SupportedLocale) || 'ar'
const fallbackLocale = (import.meta.env.VITE_FALLBACK_LOCALE as SupportedLocale) || 'en'

const messages = {
  ar: {
    app: {
      name: import.meta.env.VITE_APP_NAME || 'منصة المدرسة',
    },
    common: {
      save: 'حفظ',
      cancel: 'إلغاء',
      close: 'إغلاق',
      loading: 'جاري التحميل...'
    }
  },
  en: {
    app: {
      name: import.meta.env.VITE_APP_NAME || 'School Platform',
    },
    common: {
      save: 'Save',
      cancel: 'Cancel',
      close: 'Close',
      loading: 'Loading...'
    }
  }
}

export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: defaultLocale,
  fallbackLocale,
  messages,
})

export function setDocumentDirByLocale(locale: SupportedLocale) {
  const rtlLocales = new Set<SupportedLocale>(['ar'])
  const isRTL = rtlLocales.has(locale)
  document.documentElement.setAttribute('dir', isRTL ? 'rtl' : 'ltr')
  document.documentElement.lang = locale
}

// Initialize dir based on default
if (typeof document !== 'undefined') {
  setDocumentDirByLocale(defaultLocale)
}