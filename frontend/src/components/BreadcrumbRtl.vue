<template>
  <nav class="breadcrumb" aria-label="breadcrumb" dir="rtl">
    <div class="breadcrumb__row">
      <ol class="breadcrumb__list" ref="listEl">
        <li v-if="collapsedCount > 0" class="breadcrumb__item">
          <button class="breadcrumb__more" @click="expanded = !expanded" :aria-expanded="expanded">
            +{{ collapsedCount }}
          </button>
          <ul v-if="expanded" class="breadcrumb__dropdown" @keydown.esc="expanded=false">
            <li v-for="(c,idx) in collapsedItems" :key="idx">
              <a :href="c.href" @click.prevent="goTo(c)">{{ c.label }}</a>
            </li>
          </ul>
        </li>
        <li v-for="(crumb, index) in visibleCrumbs" :key="crumb.key" class="breadcrumb__item">
          <a
            v-if="index < visibleCrumbs.length - 1"
            :href="crumb.href"
            class="breadcrumb__link"
            @click.prevent="goTo(crumb)"
          >
            {{ crumb.label }}
          </a>
          <span v-else class="breadcrumb__current" aria-current="page">{{ crumb.label }}</span>
          <span v-if="index < visibleCrumbs.length - 1" class="breadcrumb__sep">›</span>
        </li>
      </ol>

      <div class="breadcrumb__search" @keydown.down.prevent="focusFirstOption">
        <input
          ref="searchInput"
          v-model="query"
          type="text"
          class="breadcrumb__input"
          :placeholder="placeholder"
          :aria-label="placeholder"
          @input="onQuery"
          @keydown.enter.prevent="openHighlightedOrExact"
          @keydown.esc="hideResults"
        />
        <ul v-if="showResults" class="breadcrumb__results" role="listbox">
          <li
            v-for="(opt, i) in filteredOptions"
            :key="opt.key"
            :class="['breadcrumb__option', { 'is-active': i === activeIndex }]"
            role="option"
            @mouseenter="activeIndex = i"
            @mouseleave="activeIndex = -1"
            @click="goTo(opt)"
          >
            {{ opt.label }}
            <small class="breadcrumb__option-path">{{ opt.path }}</small>
          </li>
        </ul>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter, RouteLocationNormalizedLoaded } from 'vue-router'

type Crumb = { key: string; label: string; href: string; name?: string; path?: string }

const router = useRouter()
const route = useRoute()
const placeholder = 'ابحث هنا باسم الصفحة…'

const expanded = ref(false)
const listEl = ref<HTMLOListElement | null>(null)
const searchInput = ref<HTMLInputElement | null>(null)
const query = ref('')
const showResults = ref(false)
const activeIndex = ref(-1)

// 1) تاريخ تنقل تراكمي عبر sessionStorage
const STORAGE_KEY = 'rtl_breadcrumb_history'
const historyState = reactive<{ items: Crumb[] }>({ items: [] })

function labelFromRoute(r: RouteLocationNormalizedLoaded | any): string {
  return (r.meta?.titleAr as string) || (r.meta?.title as string) || (r.name as string) || (r.path as string)
}

function buildCrumbFromRoute(r: RouteLocationNormalizedLoaded): Crumb {
  const label = labelFromRoute(r)
  return { key: `${r.fullPath}`, label, href: r.fullPath, name: r.name as string, path: r.path as string }
}

function normalizedKey(c: Pick<Crumb, 'href'|'name'|'path'>): string {
  // Prefer a stable identifier: route name, then static path, then href without query/hash
  const byName = (c.name || '').toString()
  if (byName) return byName
  const byPath = (c.path || '').toString()
  if (byPath) return byPath
  try {
    const href = c.href || ''
    const iHash = href.indexOf('#')
    const noHash = iHash >= 0 ? href.slice(0, iHash) : href
    const iQuery = noHash.indexOf('?')
    return iQuery >= 0 ? noHash.slice(0, iQuery) : noHash
  } catch {
    return c.href
  }
}

function loadHistory() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed: Crumb[] = JSON.parse(raw)
      // Deduplicate existing stored items by normalized key while preserving order (first occurrence wins)
      const seen = new Set<string>()
      const cleaned: Crumb[] = []
      for (const c of parsed) {
        const k = normalizedKey(c)
        if (!seen.has(k)) { seen.add(k); cleaned.push(c) }
      }
      historyState.items = cleaned
    }
  } catch {}
}

function saveHistory() {
  try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(historyState.items)) } catch {}
}

function pushIfNew(c: Crumb) {
  const key = normalizedKey(c)
  // Remove any previous entries that match the same normalized key
  const remaining = historyState.items.filter((x) => normalizedKey(x) !== key)
  historyState.items = [...remaining, c] as any
  saveHistory()
}

onMounted(() => {
  loadHistory()
  pushIfNew(buildCrumbFromRoute(route))
})

watch(
  () => route.fullPath,
  () => {
    pushIfNew(buildCrumbFromRoute(route))
  }
)

function goTo(c: Crumb) {
  expanded.value = false
  showResults.value = false
  router.push(c.href)
}

// 2) البحث
const allOptions = computed<Crumb[]>(() => {
  return router
    .getRoutes()
    .filter((r) => !r.path.includes(':'))
    .map((r) => ({ key: r.path, label: (r.meta as any)?.titleAr || (r.name as string) || r.path, href: r.path, path: r.path }))
})

const filteredOptions = computed(() => {
  const q = query.value.trim()
  if (!q) return []
  const lower = q.toLowerCase()
  return allOptions.value.filter((o) => (o.label || '').toString().toLowerCase().includes(lower)).slice(0, 8)
})

function onQuery() {
  showResults.value = !!query.value.trim()
  activeIndex.value = filteredOptions.value.length ? 0 : -1
}
function hideResults() {
  showResults.value = false
}
function openHighlightedOrExact() {
  const exact = filteredOptions.value.find((o) => o.label === query.value.trim())
  const target = exact || filteredOptions.value[activeIndex.value]
  if (target) goTo(target)
}
function focusFirstOption() {
  if (filteredOptions.value.length) activeIndex.value = 0
}

// 3) إدارة الطيّ
const maxVisible = ref(4)
const visibleCrumbs = computed(() => {
  const items = historyState.items
  if (items.length <= maxVisible.value) return items
  const start = items.length - maxVisible.value
  return items.slice(start)
})
const collapsedItems = computed(() => {
  const items = historyState.items
  if (items.length <= maxVisible.value) return []
  const end = items.length - maxVisible.value
  return items.slice(0, end)
})
const collapsedCount = computed(() => collapsedItems.value.length)
</script>

<style scoped>
.breadcrumb { background: var(--bc-bg, #0f3a4a); color: #e6f4f1; padding: 6px 9px; border-bottom: 1px solid rgba(255,255,255,.08); border-radius: 0; width: 100vw; margin-inline: calc(50% - 50vw); font-size: 0.75em; }
.breadcrumb__row { display: flex; align-items: center; gap: 9px; justify-content: space-between; }
.breadcrumb__list { list-style: none; display: flex; align-items: center; gap: 6px; margin: 0; padding: 0; }
.breadcrumb__item { position: relative; }
.breadcrumb__link { color: #c9f1ff; text-decoration: none; font-weight: 500; }
.breadcrumb__link:hover { text-decoration: underline; }
.breadcrumb__current { color: #fff; font-weight: 600; }
.breadcrumb__sep { margin: 0 3px; opacity: .6; }
.breadcrumb__more { background: transparent; border: 1px solid rgba(255,255,255,.25); color: #e6f4f1; border-radius: 6px; padding: 2px 5px; cursor: pointer; }
.breadcrumb__dropdown { position: absolute; top: 21px; inset-inline-end: 0; background: #113e50; border: 1px solid rgba(255,255,255,.15); border-radius: 8px; min-width: 150px; padding: 6px; z-index: 10; }
.breadcrumb__dropdown a { color: #e6f4f1; display: block; padding: 5px 6px; border-radius: 6px; text-decoration: none; }
.breadcrumb__dropdown a:hover { background: rgba(255,255,255,.07); }

.breadcrumb__search { position: relative; min-width: 195px; }
.breadcrumb__input { width: 100%; direction: rtl; background: #0c2f3c; color: #e6f4f1; border: 1px solid rgba(255,255,255,.18); border-radius: 8px; padding: 4px 8px; }
.breadcrumb__results { position: absolute; top: 27px; inset-inline: 0; background: #113e50; border: 1px solid rgba(255,255,255,.15); border-radius: 8px; max-height: 195px; overflow: auto; z-index: 20; }
.breadcrumb__option { padding: 6px 8px; cursor: pointer; color: #e6f4f1; display: flex; justify-content: space-between; gap: 6px; }
.breadcrumb__option:hover, .breadcrumb__option.is-active { background: rgba(255,255,255,.08); }
.breadcrumb__option-path { opacity: .75; }

@media (max-width: 640px) {
  .breadcrumb__row { flex-direction: column; align-items: stretch; gap: 6px; }
  .breadcrumb__search { min-width: 100%; }
}
</style>