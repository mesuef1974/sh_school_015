<template>
  <div class="print-trigger-wrapper d-inline-flex align-items-center">
    <button ref="btnEl" class="btn btn-sm btn-outline-primary" type="button" @click="toggle" :title="'خيارات الطباعة'" aria-haspopup="dialog" :aria-expanded="open ? 'true' : 'false'">
      <Icon icon="solar:printer-bold-duotone" />
    </button>

    <div v-if="open" ref="panelEl" class="print-panel shadow-lg" role="dialog" aria-modal="true" aria-label="لوحة خيارات الطباعة">
      <div class="d-flex align-items-center gap-2 mb-2">
        <Icon icon="solar:printer-bold-duotone" class="text-primary" />
        <h6 class="m-0">طباعة الصفحة</h6>
        <button class="btn-close ms-auto" @click="close" aria-label="إغلاق"></button>
      </div>

      <!-- خيارات عامة -->
      <div class="row g-2 mb-3">
        <div class="col-auto">
          <label class="form-label small">الاتجاه</label>
          <select class="form-select form-select-sm" v-model="orientation">
            <option value="portrait">طولي</option>
            <option value="landscape">عرضي</option>
          </select>
        </div>
        <div class="col-auto">
          <label class="form-label small">الهامش</label>
          <select class="form-select form-select-sm" v-model.number="margin">
            <option :value="0.5">0.5 سم</option>
            <option :value="1">1 سم</option>
            <option :value="1.5">1.5 سم</option>
            <option :value="2">2 سم</option>
          </select>
        </div>
        <div class="col-auto">
          <label class="form-label small">المقياس</label>
          <select class="form-select form-select-sm" v-model.number="scale">
            <option :value="50">50%</option>
            <option :value="60">60%</option>
            <option :value="70">70%</option>
            <option :value="80">80%</option>
            <option :value="90">90%</option>
            <option :value="100">100%</option>
            <option :value="110">110%</option>
          </select>
        </div>
        <div class="col-auto">
          <label class="form-label small">الكثافة</label>
          <select class="form-select form-select-sm" v-model="density">
            <option value="normal">عادية</option>
            <option value="compact">مضغوطة</option>
          </select>
        </div>
        <div class="col-auto d-flex align-items-end">
          <div class="form-check form-switch" title="إخفاء الأزرار والحقول داخل المحتوى أثناء الطباعة فقط">
            <input class="form-check-input" type="checkbox" id="pp-clean" v-model="clean" />
            <label class="form-check-label" for="pp-clean">وضع نظيف</label>
          </div>
        </div>
        <div class="col-auto d-flex align-items-end">
          <div class="form-check form-switch" title="قصّ أي فائض بعد الصفحة الأولى لضمان صفحة واحدة">
            <input class="form-check-input" type="checkbox" id="pp-one" v-model="onePage" />
            <label class="form-check-label" for="pp-one">صفحة واحدة</label>
          </div>
        </div>
        <div class="col-auto d-flex align-items-end">
          <div class="form-check form-switch" title="إظهار/إخفاء حدود خلايا الجداول">
            <input class="form-check-input" type="checkbox" id="pp-grid" v-model="grid" />
            <label class="form-check-label" for="pp-grid">إطار الجدول</label>
          </div>
        </div>
      </div>

      <!-- اختيار بطاقات للطباعة -->
      <div class="mb-2">
        <div class="d-flex align-items-center gap-2 mb-1">
          <Icon icon="solar:layers-bold-duotone" class="text-secondary" />
          <strong class="small">اختر ما تريد طباعته من الصفحة</strong>
          <button class="btn btn-sm btn-outline-secondary ms-auto" @click="scanCards">تحديث القائمة</button>
          <button class="btn btn-sm btn-outline-secondary" @click="selectAll">تحديد الكل</button>
          <button class="btn btn-sm btn-outline-secondary" @click="clearAll">مسح التحديد</button>
        </div>
        <div class="printables-list">
          <div v-if="cards.length === 0" class="text-muted small">لا توجد بطاقات قابلة للطباعة في هذه الصفحة.</div>
          <div v-for="c in cards" :key="c.id" class="mb-2">
            <div class="form-check">
              <input class="form-check-input" type="checkbox" :id="`print-card-${c.id}`" v-model="c.selected" />
              <label class="form-check-label" :for="`print-card-${c.id}`">{{ c.label }}</label>
            </div>
            <div v-if="c.cols && c.cols.length" class="mt-1 ms-4">
              <div class="d-flex align-items-center gap-2 mb-1">
                <span class="small text-muted">تخصيص أعمدة هذه البطاقة (للطباعة فقط)</span>
                <button type="button" class="btn btn-sm btn-outline-secondary ms-auto" @click="selectAllCols(c)">تحديد كل الأعمدة</button>
                <button type="button" class="btn btn-sm btn-outline-secondary" @click="invertCols(c)">عكس التحديد</button>
              </div>
              <div class="d-flex flex-wrap gap-2">
                <label class="form-check form-check-inline small" v-for="col in c.cols" :key="col.index">
                  <input class="form-check-input" type="checkbox" v-model="col.selected" />
                  <span class="form-check-label">{{ col.label || ('عمود #' + col.index) }}</span>
                </label>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="d-flex gap-2">
        <button class="btn btn-primary btn-sm" @click="printPage">طباعة الصفحة</button>
        <button class="btn btn-success btn-sm" :disabled="!anySelected" @click="printSelected">طباعة العناصر المحددة</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed, watch } from 'vue';
import { useWingPrefs } from '../../shared/composables/useWingPrefs';

type CardItem = { id: number; label: string; el: Element; selected: boolean; cols: { index: number; label: string; selected: boolean }[] };

const open = ref(false);
const orientation = ref<'portrait'|'landscape'>('portrait');
const margin = ref<number>(1);
const scale = ref<number>(100);
const density = ref<'normal'|'compact'>('normal');
const clean = ref<boolean>(false);
const grid = ref<boolean>(true);
const onePage = ref<boolean>(false); // إجبار صفحة واحدة (يقصّ الفائض)

// Load/save defaults from centralized WingPrefs (print_defaults)
const prefs = useWingPrefs();
const { print_defaults } = prefs as any;

onMounted(() => {
  try {
    if (print_defaults?.value) {
      orientation.value = print_defaults.value.orientation || 'portrait';
      margin.value = typeof print_defaults.value.margin_cm === 'number' ? print_defaults.value.margin_cm : 1;
      scale.value = (print_defaults.value.scale as any) ?? 100;
      density.value = (print_defaults.value.density as any) ?? 'normal';
      clean.value = !!print_defaults.value.clean;
      grid.value = !!print_defaults.value.grid;
      onePage.value = !!print_defaults.value.one_page;
    }
  } catch {}
});

// Persist changes to prefs when user adjusts options
watch([orientation, margin, scale, density, clean, grid, onePage], () => {
  try {
    const next = {
      orientation: orientation.value,
      margin_cm: margin.value,
      scale: scale.value as any,
      density: density.value as any,
      clean: clean.value,
      grid: grid.value,
      one_page: onePage.value,
    } as any;
    // @ts-ignore
    prefs.set('print_defaults', next);
  } catch {}
}, { deep: false });

const panelEl = ref<HTMLElement|null>(null);
const btnEl = ref<HTMLElement|null>(null);
const cards = ref<CardItem[]>([]);

function toggle() {
  open.value = !open.value;
  if (open.value) {
    scanCards();
    attachGlobal();
  } else {
    detachGlobal();
  }
}
function close() { open.value = false; detachGlobal(); }

function onKey(ev: KeyboardEvent) { if (ev.key === 'Escape') close(); }
function onDocClick(ev: MouseEvent) {
  if (!open.value) return;
  const t = ev.target as Node;
  if (panelEl.value && !panelEl.value.contains(t) && !(btnEl.value && btnEl.value.contains(t))) {
    close();
  }
}

function attachGlobal() {
  document.addEventListener('keydown', onKey);
  document.addEventListener('click', onDocClick);
}
function detachGlobal() {
  document.removeEventListener('keydown', onKey);
  document.removeEventListener('click', onDocClick);
}

onUnmounted(detachGlobal);

function getTableColumns(el: Element): { index: number; label: string; selected: boolean }[] {
  try {
    const table = el.querySelector('table, .table, .print-table') as HTMLTableElement | null;
    if (!table) return [];
    // Prefer thead > th
    const headers = Array.from(table.querySelectorAll('thead tr th')) as HTMLElement[];
    let labels: string[] = [];
    if (headers.length) {
      labels = headers.map((th) => (th.innerText || th.textContent || '').trim());
    } else {
      // Fallback: first row td
      const firstRow = table.querySelector('tbody tr');
      if (firstRow) {
        const tds = Array.from(firstRow.querySelectorAll('td')) as HTMLElement[];
        labels = tds.map((td, i) => (td.getAttribute('data-col-label') || (td.innerText || '').trim() || `عمود #${i + 1}`));
      }
    }
    return labels.map((label, i) => ({ index: i + 1, label, selected: false }));
  } catch {
    return [];
  }
}

function getPageTitle(): string {
  try {
    // Prefer the unified WingPageHeader title
    const h = document.querySelector('.header-bar .fw-bold');
    const t = (h && (h as HTMLElement).innerText) ? (h as HTMLElement).innerText.trim() : '';
    if (t) return t;
  } catch {}
  try {
    // Fallback to document title (i18n app name might be there)
    return (document.title || '').trim();
  } catch {}
  return 'الصفحة';
}

function normalizeLabel(s: string): string {
  return (s || '').replace(/\s+/g, ' ').trim();
}

function scanCards() {
  try {
    const list: CardItem[] = [];
    const containers = new Set<Element>();
    // 1) Primary: common card-like containers across the app
    const selectors = [
      '.card',
      '.outlined-card',
      '.auto-card',
      '.ds-card',
      '.panel',
      '.widget',
      '.timetable-card',
      '[data-printable]'
    ].join(',');
    document.querySelectorAll(selectors).forEach((el) => containers.add(el as Element));

    // 2) Standalone tables (not wrapped in known containers)
    const tables = Array.from(document.querySelectorAll('table.print-table, table.table')) as Element[];
    for (const tb of tables) {
      // Skip if table is inside an already collected container
      let parent: Element | null = tb.parentElement;
      let foundContainer: Element | null = null;
      while (parent && parent !== document.body) {
        if ((parent as HTMLElement).matches(selectors)) { foundContainer = parent; break; }
        parent = parent.parentElement;
      }
      containers.add(foundContainer || tb);
    }

    const pageTitle = getPageTitle();
    let id = 1;
    for (const el of Array.from(containers.values())) {
      // Skip if this is inside the floating panel itself
      if (panelEl.value && panelEl.value.contains(el)) continue;
      // Skip explicit opt-out
      if ((el as HTMLElement).getAttribute('data-print-exclude') === 'true') continue;
      // Skip invisible elements
      const style = window.getComputedStyle(el as HTMLElement);
      if (style.display === 'none' || style.visibility === 'hidden') continue;

      let label = normalizeLabel(findCardLabel(el));
      if (!label) {
        // Use page title as a neutral fallback without numbering
        label = pageTitle || 'بطاقة';
      }
      // Always sync the computed label to the element to ensure consistency across pages
      try {
        (el as HTMLElement).setAttribute('aria-label', label);
        (el as HTMLElement).setAttribute('data-title', label);
      } catch {}
      const cols = getTableColumns(el);
      list.push({ id: id++, label, el, selected: false, cols });
    }
    cards.value = list;
  } catch { cards.value = []; }
}

function findCardLabel(el: Element): string {
  try {
    // 1) Prefer explicit heading elements inside the container
    const h = el.querySelector('h1, h2, h3, h4, h5, h6, [role="heading"], .card-title, .card-title-maroon, .card-header');
    if (h && (h as HTMLElement).innerText?.trim()) return (h as HTMLElement).innerText.trim();

    // 2) Attributes provided by pages/components
    const attr = (el.getAttribute('aria-label') || el.getAttribute('data-title') || '').trim();
    if (attr) return attr;

    // 3) Table-specific cues when el is a table or contains one
    const table = (el.matches('table') ? el : el.querySelector('table')) as HTMLTableElement | null;
    if (table) {
      // caption element
      const cap = table.querySelector('caption');
      if (cap && (cap as HTMLElement).innerText?.trim()) return (cap as HTMLElement).innerText.trim();
      // aria-labelledby
      const lblId = table.getAttribute('aria-labelledby');
      if (lblId) {
        const lab = document.getElementById(lblId);
        if (lab && lab.innerText?.trim()) return lab.innerText.trim();
      }
      // nearest previous sibling heading
      let prev: Element | null = table;
      while (prev && prev.previousElementSibling) {
        prev = prev.previousElementSibling as Element;
        if (!prev) break;
        const hh = prev.matches('h1, h2, h3, h4, h5, h6, [role="heading"], .card-title, .card-title-maroon, .card-header')
          ? prev
          : prev.querySelector('h1, h2, h3, h4, h5, h6, [role="heading"], .card-title, .card-title-maroon, .card-header');
        if (hh && (hh as HTMLElement).innerText?.trim()) return (hh as HTMLElement).innerText.trim();
        // stop climbing if we hit another large container
        if (prev.matches('.card, .outlined-card, .ds-card, .panel, .widget')) break;
      }
    }

    // 4) KPI-style cards often use a muted small label as the first element in the body
    const kpi = el.querySelector('.card-body .text-muted.small, .card-body .small.text-muted, .card-body .text-muted');
    if (kpi && (kpi as HTMLElement).innerText?.trim()) return (kpi as HTMLElement).innerText.trim();

    // 5) Fallback to first strong text
    const st = el.querySelector('strong');
    if (st && (st as HTMLElement).innerText?.trim()) return (st as HTMLElement).innerText.trim();

    // 6) Generic fallback: first non-empty text from shallow elements inside the container/body
    const body = el.querySelector('.card-body') || el;
    const walkers = Array.from(body.querySelectorAll('*')) as HTMLElement[];
    for (const node of walkers) {
      // Skip buttons/inputs/links to avoid control labels
      const tag = node.tagName.toLowerCase();
      if (["button","input","select","textarea","a","svg"].includes(tag)) continue;
      const txt = (node.innerText || node.textContent || '').replace(/\s+/g, ' ').trim();
      if (txt && txt.length > 0) {
        // Limit overly long blobs
        return txt.length > 80 ? txt.slice(0, 80) + '…' : txt;
      }
    }
  } catch {}
  // Last resort: neutral generic label (no numbering)
  return 'بطاقة';
}

const anySelected = computed(() => cards.value.some(c => c.selected));

function selectAll() { cards.value = cards.value.map(c => ({ ...c, selected: true })); }
function clearAll() { cards.value = cards.value.map(c => ({ ...c, selected: false })); }

// Per-card column bulk actions
function selectAllCols(card: CardItem) {
  try {
    const updated = card.cols.map(col => ({ ...col, selected: true }));
    // replace the specific card object to keep reactivity predictable
    cards.value = cards.value.map(c => (c.id === card.id ? { ...c, cols: updated } : c));
  } catch {}
}
function invertCols(card: CardItem) {
  try {
    const updated = card.cols.map(col => ({ ...col, selected: !col.selected }));
    cards.value = cards.value.map(c => (c.id === card.id ? { ...c, cols: updated } : c));
  } catch {}
}

function buildBodyClasses(): string[] {
  const classes: string[] = [];
  if (density.value === 'compact') classes.push('print-compact');
  if (!grid.value) classes.push('print-no-grid');
  // scale mapping extended down to 50%
  if (scale.value === 50) classes.push('print-scale-50');
  else if (scale.value === 60) classes.push('print-scale-60');
  else if (scale.value === 70) classes.push('print-scale-70');
  else if (scale.value === 80) classes.push('print-scale-80');
  else if (scale.value === 90) classes.push('print-scale-90');
  else if (scale.value === 110) classes.push('print-scale-110');
  else classes.push('print-scale-100');
  return classes;
}

// Build body classes without scale (used for selective cards printing so scale applies only to selected cards)
function buildBodyClassesNoScale(): string[] {
  const classes: string[] = [];
  if (density.value === 'compact') classes.push('print-compact');
  if (!grid.value) classes.push('print-no-grid');
  return classes;
}

function buildOnePageCss(ornt: 'portrait'|'landscape', marginCm: number): string {
  if (!onePage.value) return '';
  const pageHeight = ornt === 'portrait' ? 29.7 : 21.0; // cm
  const safeMargin = Math.max(0, Math.min(5, marginCm));
  const contentMax = Math.max(5, pageHeight - (safeMargin * 2));
  // Limit main containers to a single printed page and clip overflow
  return `@media print {\n  #app, main, .main-content, .page-grid, .page-grid-wide, .container, .container-fluid {\n    max-height: ${contentMax}cm !important;\n    overflow: hidden !important;\n  }\n}`;
}

function mergeCss(a: string, b: string): string {
  const aa = (a || '').trim();
  const bb = (b || '').trim();
  if (aa && bb) return aa + "\n" + bb;
  return aa || bb;
}

function printPage() {
  const extraCss = buildOnePageCss(orientation.value, margin.value);
  const opts: any = { orientation: orientation.value, marginCm: margin.value, addBodyClasses: buildBodyClasses(), clean: clean.value, extraCss };
  // @ts-ignore
  const pm = window.printManager || (globalThis as any).printManager || {};
  pm?.print?.(opts);
  close();
}

function buildPerCardCss(selectedCards: CardItem[]): string {
  // Generate CSS to (a) hide unchecked columns per card and (b) apply scale only to selected cards
  // We scope all rules using a temporary data attribute per selected card
  const rules: string[] = [];
  const scalePtMap: Record<number, string> = { 50: '6pt', 60: '7pt', 70: '8pt', 80: '9pt', 90: '10pt', 100: '11pt', 110: '12pt' };
  const scalePt = scalePtMap[scale.value] || '11pt';

  let idCounter = 1;
  for (const c of selectedCards) {
    // Assign a stable temporary attribute to scope CSS
    const pid = `pc${Date.now()}-${idCounter++}`;
    (c.el as HTMLElement).setAttribute('data-print-id', pid);

    // 1) Column hiding per selection
    const unchecked = (c.cols || []).filter(col => !col.selected).map(col => col.index);
    if (unchecked.length) {
      const selectors: string[] = [];
      for (const idx of unchecked) {
        // Hide matching th and td for this column index within this card
        selectors.push(`[data-print-id="${pid}"] table thead tr th:nth-child(${idx})`);
        selectors.push(`[data-print-id="${pid}"] table tbody tr td:nth-child(${idx})`);
        // Also cover tfoot if present
        selectors.push(`[data-print-id="${pid}"] table tfoot tr td:nth-child(${idx})`);
      }
      rules.push(`${selectors.join(',')} { display: none !important; }`);
    }

    // 2) Apply scale only to this card by setting a base font-size on the container
    // This approximates body.print-scale-* but scoped to the selected element
    rules.push(`[data-print-id="${pid}"] { font-size: ${scalePt} !important; }`);
  }

  if (rules.length) {
    return `@media print { ${rules.join(' ')} }`;
  }
  return '';
}

function cleanupPerCardAttrs(selectedCards: CardItem[]) {
  setTimeout(() => {
    try {
      for (const c of selectedCards) (c.el as HTMLElement).removeAttribute('data-print-id');
    } catch {}
  }, 1200);
}

function printSelected() {
  const selectedCards = cards.value.filter(c => c.selected);
  const targets = selectedCards.map(c => c.el);
  const perCardCss = buildPerCardCss(selectedCards);
  const oneCss = buildOnePageCss(orientation.value, margin.value);
  const extraCss = mergeCss(perCardCss, oneCss);
  const opts: any = { orientation: orientation.value, marginCm: margin.value, addBodyClasses: buildBodyClassesNoScale(), clean: clean.value, targets, extraCss };
  // @ts-ignore
  const pm = window.printManager || (globalThis as any).printManager || {};
  if (pm?.printElements) {
    pm.printElements(opts);
  } else if (pm?.print) {
    pm.print(opts);
  } else {
    window.print();
  }
  cleanupPerCardAttrs(selectedCards);
  close();
}

// Re-scan cards when the panel opens for the first time and also on mount (in case needed)
onMounted(() => { if (open.value) scanCards(); });
</script>

<style scoped>
.print-trigger-wrapper { position: relative; }
.print-panel {
  position: fixed;
  inset-inline-end: 1rem;
  top: 5rem;
  width: min(480px, 94vw);
  background: #fff;
  border-radius: .5rem;
  padding: .75rem;
  z-index: 2050;
}
.printables-list {
  max-height: 40vh;
  overflow: auto;
  border: 1px solid #eee;
  border-radius: .375rem;
  padding: .5rem;
}
</style>
