<template>
  <section class="full-bleed d-grid gap-3">
    <div class="auto-card p-3 d-flex align-items-center gap-2 flex-wrap toolbar-card">
      <Icon icon="solar:clock-circle-bold-duotone" class="text-2xl" />
      <div class="fw-bold">جدول الجناح</div>
      <span class="vr mx-2 d-none d-sm-block"></span>

      <div class="d-flex align-items-center gap-2 flex-wrap ms-auto toolbar-controls">
        <div class="d-flex align-items-center gap-2">
          <Icon icon="solar:home-2-bold-duotone" />
          <label class="visually-hidden" for="wingSelect">اختر الجناح</label>
          <select id="wingSelect" aria-label="اختيار الجناح" class="form-select form-select-sm" v-model.number="wingId" @change="loadData">
            <option :value="null" disabled>اختر الجناح</option>
            <option v-for="(name,id) in wingOptions" :key="id" :value="Number(id)">{{ name }}</option>
          </select>
        </div>
        <div class="d-flex align-items-center gap-2">
          <Icon icon="solar:calendar-bold-duotone" />
          <label class="visually-hidden" for="dateInput">التاريخ</label>
          <input id="dateInput" aria-label="اختيار التاريخ" type="date" class="form-control form-control-sm" v-model="dateStr" @change="loadData" />
        </div>
        <div class="btn-group btn-group-sm" role="group" aria-label="وضع العرض">
          <button type="button" class="btn" :class="mode==='daily'?'btn-primary':'btn-outline-secondary'" @click="setMode('daily')">اليوم</button>
          <button type="button" class="btn" :class="mode==='weekly'?'btn-primary':'btn-outline-secondary'" @click="setMode('weekly')">أسبوع</button>
        </div>
        <DsButton size="sm" variant="outline" icon="solar:printer-bold-duotone" @click="printPage" aria-label="طباعة الجدول">طباعة</DsButton>
        <DsButton size="sm" variant="outline" icon="solar:refresh-bold-duotone" :loading="loading" @click="loadData" aria-label="تحديث البيانات">تحديث</DsButton>
      </div>
    </div>

    <!-- Print-only header -->
    <div class="auto-card p-2 print-header" aria-hidden="true">
      <div class="d-flex align-items-center gap-2">
        <Icon icon="solar:printer-bold-duotone" />
        <div class="fw-bold">
          {{ mode==='daily' ? 'جدول الجناح — ' + formattedDate + ' — ' + dayNameAr(dateStr) : 'الجدول الأسبوعي' }}
          <span v-if="wingLabel"> — {{ wingLabel }}</span>
        </div>
      </div>
    </div>

    <div v-if="loading" class="auto-card p-4 text-center">
      <Icon icon="solar:refresh-bold-duotone" class="animate-spin text-4xl" />
      <div class="text-muted mt-2 small">جاري تحميل الجدول...</div>
    </div>

    <div v-else-if="error" class="alert alert-danger">حدث خطأ أثناء التحميل: {{ error }}</div>

    <!-- Empty state -->
    <div v-else-if="isEmpty" class="auto-card p-4 text-center">
      <Icon icon="solar:inbox-line-bold-duotone" class="text-5xl mb-2" style="opacity:.4" />
      <div class="h6 mb-1">لا توجد بيانات للعرض</div>
      <div class="text-muted small" v-if="meta.reason === 'no_wing'">لا يوجد جناح مخصص لحسابك. عيّن نفسك كمشرف لجناح في لوحة الإدارة (Wing.supervisor).</div>
      <div class="text-muted small" v-else-if="meta.reason === 'no_term'">لا يوجد فصل دراسي حالي (is_current=True). أنشئ فصلًا وحدده كحالي.</div>
      <div class="text-muted small" v-else-if="meta.reason === 'no_classes'">لا توجد صفوف مرتبطة بهذا الجناح. اربط بعض الصفوف بالجناح.</div>
      <div class="text-muted small" v-else-if="meta.reason === 'no_entries_today'">لا توجد حصص مجدولة لهذا اليوم ضمن الجناح/الفصل الدراسي الحالي.</div>
      <div class="text-muted small" v-else>تحقق من اختيار الجناح والتاريخ</div>
    </div>

    <!-- Daily view: صف واحد لكل حصة -->
    <div v-else-if="mode==='daily'" class="auto-card p-0 overflow-hidden">
      <div class="p-3 d-flex align-items-center gap-2 border-bottom">
        <Icon icon="solar:calendar-date-bold-duotone" />
        <div class="fw-bold">جدول اليوم — {{ formattedDate }} — {{ dayNameAr(dateStr) }}</div>
        <span class="ms-auto small text-muted">{{ groupedDaily.total }} عنصر</span>
      </div>
      <div class="p-2">
        <div v-for="p in PERIODS" :key="'row-'+p" class="period-line">
          <span class="badge text-bg-primary no-wrap">حصة {{ p }}</span>
          <span class="text-muted small" v-if="periodTimes[p]"><Icon icon="solar:clock-circle-bold-duotone" width="14" class="me-1" />{{ timeRange(p) }}</span>
          <span class="countdown badge text-bg-light no-wrap" v-if="countdownMap[p]">{{ countdownMap[p] }}</span>
          <div class="items-inline">
            <template v-if="groupedDaily.groups[p] && groupedDaily.groups[p].length">
              <template v-for="(item, idx) in groupedDaily.groups[p]" :key="'it-'+p+'-'+item.class_id">
                <div class="period-cell" :style="{ backgroundColor: item.color || '#f5f7fb' }" :title="(item.class_name || ('صف #' + item.class_id)) + ' — ' + (item.subject_name || 'مادة') + ' — ' + (item.teacher_name || '—')">
                  <div class="cell-subject one-line">{{ item.subject_name || 'مادة' }}</div>
                  <div class="cell-teacher one-line">{{ item.teacher_name || '—' }}</div>
                </div>
              </template>
            </template>
            <span v-else class="text-muted">—</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Weekly view: جدول احترافي 7×7 ومتمركز -->
    <div v-else class="auto-card p-0 overflow-hidden">
      <div class="p-3 d-flex align-items-center gap-2 border-bottom">
        <Icon icon="solar:calendar-bold-duotone" />
        <div class="fw-bold">الجدول الأسبوعي 7×7</div>
        <span class="ms-auto small text-muted">حِصص × أيام (7 × 7)</span>
      </div>
      <div class="tt7-wrapper">
        <div class="tt7-scroller">
          <table class="tt7-table" dir="rtl" aria-label="جدول أسبوعي 7×7">
            <thead>
              <tr>
                <th class="tt7-th tt7-th-sticky tt7-th-period">الحصة</th>
                <th v-for="d in DAYS7" :key="'dh-'+d[0]" class="tt7-th">{{ d[1] }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in PERIODS" :key="'row-'+p">
                <th class="tt7-th tt7-th-period">
                  <div class="hdr-line"><span class="badge text-bg-secondary no-wrap">حصة {{ p }}</span><span class="text-muted small" v-if="periodTimes[p]"><Icon icon="solar:clock-circle-bold-duotone" width="14" class="me-1" />{{ timeRange(p) }}</span></div>
                </th>
                <td v-for="d in DAYS7" :key="'c-'+d[0]+'-'+p" class="tt7-td">
                  <div class="tt7-cell">
                    <template v-if="cellItems(d[0], p).length">
                      <div v-for="item in cellItems(d[0], p)" :key="'it-'+d[0]+'-'+p+'-'+item.class_id" class="mini-cell" :style="{ backgroundColor: item.color || '#f5f7fb' }" :title="(item.class_name || ('صف #'+item.class_id)) + ' — ' + (item.subject_name || 'مادة') + ' — ' + (item.teacher_name || '—')">
                        <div class="mini-subj one-line">{{ item.subject_name || 'مادة' }}</div>
                        <div class="mini-teacher one-line">{{ item.teacher_name || '—' }}</div>
                      </div>
                    </template>
                    <span v-else class="text-muted">—</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import DsButton from '../../../components/ui/DsButton.vue';
import { getWingMe, getWingTimetable } from '../../../shared/api/client';
import { formatDateDMY } from '../../../shared/utils/date';

const today = new Date();
const iso = (d: Date) => d.toISOString().slice(0,10);
const dateStr = ref<string>(iso(today));
const mode = ref<'daily'|'weekly'>('daily');
const loading = ref(false);
const error = ref<string | null>(null);
const wingId = ref<number | null>(null);
const wingOptions = ref<Record<number, string>>({});

const DAYS = [
  [1,'الأحد'],[2,'الاثنين'],[3,'الثلاثاء'],[4,'الأربعاء'],[5,'الخميس']
] as const;
// 7 أيام لعرض شبكة 7×7 (تتضمن الجمعة والسبت وقد تكون فارغة)
const DAYS7 = [
  [1,'الأحد'],[2,'الاثنين'],[3,'الثلاثاء'],[4,'الأربعاء'],[5,'الخميس'],[6,'الجمعة'],[7,'السبت']
] as const;
const PERIODS = [1,2,3,4,5,6,7];
const activeDay = ref<number>(1);
const activeDayStr = computed(() => String(activeDay.value));

const weekly = ref<Record<string, any[]>>({});
const dailyItems = ref<any[]>([]);
const meta = ref<Record<string, any>>({});
const periodTimes = ref<Record<number, { start: string; end: string }>>({});

const isEmpty = computed(() => (mode.value==='daily' ? dailyItems.value.length===0 : Object.values(weekly.value).every(a => (a as any[]).length===0)));
const formattedDate = computed(() => formatDateDMY(dateStr.value));

const groupedDaily = computed(() => {
  const groups: Record<number, any[]> = {};
  for (const p of PERIODS) groups[p] = [];
  for (const it of dailyItems.value) {
    if (groups[it.period_number]) groups[it.period_number].push(it);
  }
  return { groups, total: dailyItems.value.length };
});

// Derive current wing label for print header and context
const wingLabel = computed(() => {
  const id = wingId.value as number | null;
  if (!id) return '';
  const name = (wingOptions.value as any)[id];
  return name || (`جناح #${id}`);
});

function printPage() {
  try { window.print(); } catch {}
}

function dayNameAr(d: string): string {
  const N = ['الأحد','الاثنين','الثلاثاء','الأربعاء','الخميس','الجمعة','السبت'];
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(d));
  let dt: Date = m ? new Date(parseInt(m[1]), parseInt(m[2])-1, parseInt(m[3])) : new Date(d);
  if (isNaN(dt.getTime())) return '—';
  return N[dt.getDay()] || '—';
}

function setMode(m: 'daily'|'weekly') { if (mode.value !== m) { mode.value = m; loadData(); } }

function timeToHM(t: string | undefined | null): string {
  if (!t) return '';
  // Expecting 'HH:MM[:SS]' — keep HH:MM
  const m = /^(\d{2}:\d{2})/.exec(String(t));
  return m ? m[1] : String(t);
}
function timeRange(p: number): string {
  const rec = periodTimes.value[p as keyof typeof periodTimes.value] as any;
  if (!rec) return '';
  const s = timeToHM(rec.start);
  const e = timeToHM(rec.end);
  return s && e ? `${s} — ${e}` : s || e || '';
}

// إرجاع عناصر الخلية لليوم d (1..7) والحصة p (1..7)
function cellItems(d: number, p: number) {
  const arr = weekly.value[String(d)] || [];
  return arr.filter((i: any) => Number(i.period_number) === p);
}

function ensureWeeklyShape() {
  // ضَمَن وجود مفاتيح 1..7 حتى إن لم يرجعها الـ API
  for (let d = 1; d <= 7; d++) {
    if (!weekly.value[String(d)]) weekly.value[String(d)] = [];
  }
}

// ==== Countdown logic ====
const countdownMap = ref<Record<number, string>>({});
let timerHandle: number | null = null;

function parseDateTime(dIso: string, hm: string | undefined): Date | null {
  if (!dIso || !hm) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(dIso));
  const t = /^(\d{2}):(\d{2})(?::(\d{2}))?/.exec(String(hm));
  if (!m || !t) return null;
  const y = parseInt(m[1], 10);
  const mo = parseInt(m[2], 10) - 1;
  const dd = parseInt(m[3], 10);
  const hh = parseInt(t[1], 10);
  const mi = parseInt(t[2], 10);
  const ss = t[3] ? parseInt(t[3], 10) : 0;
  return new Date(y, mo, dd, hh, mi, ss);
}

function fmtHMS(totalSeconds: number): string {
  if (totalSeconds < 0) totalSeconds = 0;
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = Math.floor(totalSeconds % 60);
  const pad = (n: number) => String(n).padStart(2, '0');
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
}

function updateCountdowns() {
  const map: Record<number, string> = {};
  const now = new Date();
  for (const p of PERIODS) {
    const rec = periodTimes.value[p as keyof typeof periodTimes.value] as any;
    if (!rec) { map[p] = ''; continue; }
    const start = parseDateTime(dateStr.value, rec.start);
    const end = parseDateTime(dateStr.value, rec.end);
    if (!start || !end) { map[p] = ''; continue; }
    if (now >= start && now <= end) {
      const remain = Math.floor((end.getTime() - now.getTime()) / 1000);
      map[p] = fmtHMS(remain);
    } else {
      map[p] = '';
    }
  }
  countdownMap.value = map;
}

function startTimer() {
  stopTimer();
  updateCountdowns();
  timerHandle = window.setInterval(updateCountdowns, 1000);
}
function stopTimer() {
  if (timerHandle != null) { window.clearInterval(timerHandle); timerHandle = null; }
}

async function loadMe() {
  try {
    const me = await getWingMe();
    const map: Record<number,string> = {};
    (me.wings?.ids || []).forEach((id: number, idx: number) => { map[id] = me.wings?.names?.[idx] || ('جناح #' + id); });
    wingOptions.value = map;
    if (!wingId.value) {
      const keys = Object.keys(map);
      if (keys.length) wingId.value = Number(keys[0]);
    }
  } catch {
    wingOptions.value = {} as any;
  }
}

async function loadData() {
  if (!wingId.value) { await loadMe(); if (!wingId.value) return; }
  loading.value = true; error.value = null;
  try {
    const res = await getWingTimetable({ wing_id: wingId.value || undefined, date: dateStr.value, mode: mode.value });
    // Extract period_times to local map
    const m = (res as any).meta?.period_times || {};
    const pt: Record<number, { start: string; end: string }> = {};
    Object.keys(m).forEach(k => {
      const v = (m as any)[k];
      if (Array.isArray(v) && v.length >= 2) {
        pt[Number(k)] = { start: String(v[0]), end: String(v[1]) };
      } else if (v && typeof v === 'object') {
        const s = (v as any).start || (v as any).start_time;
        const e = (v as any).end || (v as any).end_time;
        if (s || e) pt[Number(k)] = { start: String(s || ''), end: String(e || '') } as any;
      }
    });
    periodTimes.value = pt;

    if ((res as any).mode === 'weekly') {
      weekly.value = (res as any).days || {};
      ensureWeeklyShape();
      if (!weekly.value[activeDayStr.value]) activeDay.value = 1;
    } else {
      dailyItems.value = (res as any).items || [];
    }
    // After data load, (re)start countdown timer for daily mode
    if (mode.value === 'daily') startTimer(); else stopTimer();
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || String(e);
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await loadMe();
  await loadData();
  startTimer();
});

onBeforeUnmount(() => {
  stopTimer();
});
</script>

<style scoped>
.full-bleed { width: 100vw; margin-inline: calc(50% - 50vw); }
section.full-bleed > * { width: 95%; margin-inline: auto; }
@media (max-width: 576px) { section.full-bleed > * { width: 100%; } }

.toolbar-controls .btn { white-space: nowrap; }

.slot-card { border: 1px solid rgba(0,0,0,0.06); border-radius: 12px; background: #fff; box-shadow: 0 4px 12px rgba(0,0,0,.05); }
.slot-card .icon-wrap { width: 30px; height: 30px; display:grid; place-items:center; color: #8a1538; background: rgba(0,0,0,0.04); border-radius: 8px; }
.tiny { font-size: .8rem; }

.days-tabs { background: linear-gradient(135deg, #f8f9fa 0%, #edf1f5 100%); border-bottom: 1px solid #e9ecef; }
.no-wrap { white-space: nowrap; }
.one-line { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
/* Prevent content from forcing wrap: allow text to shrink within flex container */
.slot-card .flex-fill { min-width: 0; }
.slot-card .icon-wrap, .slot-card .badge { flex-shrink: 0; }
/* Strong single-line header utility for period headers */
.hdr-line { display: flex; align-items: center; gap: .5rem; white-space: nowrap; flex-wrap: nowrap; }
.hdr-line > * { flex-shrink: 0; }
.hdr-line .badge { white-space: nowrap; }

/* 7×7 weekly grid styles */
.tt7-wrapper { display: flex; justify-content: center; padding: 12px; }
.tt7-scroller { max-width: 1200px; width: 100%; margin-inline: auto; overflow: auto; }
.tt7-table { width: 100%; border-collapse: separate; border-spacing: 0; background: #fff; table-layout: fixed; }
.tt7-th { background: linear-gradient(135deg, #f8f9fa 0%, #edf1f5 100%); color: #333; font-weight: 700; text-align: center; padding: .75rem; border-bottom: 2px solid #e0e6ef; white-space: nowrap; }
.tt7-th-period { text-align: right; position: sticky; inset-inline-start: 0; background: #fafbfc; border-inline-end: 1px solid #eef2f7; min-width: 180px; z-index: 1; }
.tt7-td { vertical-align: top; padding: .5rem; border-bottom: 1px solid #f0f2f5; border-inline-start: 1px solid #f6f7f9; height: 120px; }
.tt7-table tr:hover td { background: #fafbff; }
.tt7-cell { display: block; max-height: 100%; overflow: auto; padding: 2px; }
.mini-cell { width: 100%; display: flex; flex-direction: column; gap: 2px; padding: .35rem .5rem; border: 1px solid rgba(0,0,0,0.06); border-radius: 10px; background: #f5f7fb; box-shadow: 0 2px 6px rgba(0,0,0,.04); }
.mini-subj { font-weight: 700; color: #1f2937; line-height: 1.1; }
.mini-teacher { font-size: .82rem; color: #6b7280; line-height: 1.1; }
@media (max-width: 768px) { .tt7-th-period { position: static; } .mini-cell { flex-basis: 140px; } }

/* New single-row daily layout */
.period-line {
  display: flex;
  align-items: center;
  gap: .6rem;
  white-space: nowrap;
  overflow-x: auto;
  padding: .5rem .75rem;
  border-bottom: 1px solid #f0f0f0;
}
.period-line .items-inline { display: inline-flex; align-items: stretch; gap: .5rem; }
.period-line .countdown { font-weight: 600; }
/* Professional inline cells for each class in the period */
.period-cell {
  display: inline-flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  width: 160px;
  height: 64px;
  padding: .35rem .5rem;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 10px;
  background: #f5f7fb;
  box-shadow: 0 2px 6px rgba(0,0,0,.04);
}
.cell-subject {
  font-weight: 700;
  color: #1f2937; /* dark slate */
  line-height: 1.1;
}
.cell-teacher {
  font-size: .82rem;
  color: #6b7280; /* muted */
  line-height: 1.1;
}
@media (max-width: 576px) {
  .period-cell { min-width: 120px; max-width: 180px; }
}
/* Print: ensure readable high-contrast */
@media print {
  .period-cell { background: #fff !important; border-color: #ccc !important; box-shadow: none !important; }
  .cell-subject { color: #000 !important; }
  .cell-teacher { color: #333 !important; }
}
</style>

<style>
@media print {
  @page { size: A4 portrait; margin: 10mm; }
  body { background: #fff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .navbar-maronia, .page-footer { display: none !important; }
  .toolbar-card, .days-tabs { display: none !important; }
  .print-header { display: block !important; }
  .auto-card { box-shadow: none !important; border: none !important; }
  .slot-card { box-shadow: none !important; break-inside: avoid; page-break-inside: avoid; }
  .full-bleed, section.full-bleed > * { width: 100% !important; margin: 0 !important; }
}
/* Hide print header on screen */
.print-header { display: none; }
</style>