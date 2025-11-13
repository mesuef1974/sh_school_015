<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" />

    <!-- شريط أدوات بسيط للفلاتر -->
    <div class="card p-3">
      <div class="row g-3 align-items-end">
        <div class="col-md-3 col-12">
          <label for="from" class="form-label">من</label>
          <input id="from" type="date" class="form-control" v-model="from" @change="applyFilters" />
        </div>
        <div class="col-md-3 col-12">
          <label for="to" class="form-label">إلى</label>
          <input id="to" type="date" class="form-control" v-model="to" @change="applyFilters" />
        </div>
        <div class="col-md-3 col-12">
          <label for="status" class="form-label">الحالة</label>
          <select id="status" class="form-select" v-model="status" @change="applyFilters">
            <option value="">الكل</option>
            <option value="open">مفتوح</option>
            <option value="in_progress">قيد المعالجة</option>
            <option value="resolved">تم الحل</option>
            <option value="archived">مؤرشفة</option>
          </select>
        </div>
        <div class="col-md-3 col-12">
          <label for="q" class="form-label">بحث</label>
          <input id="q" type="search" class="form-control" v-model.trim="q" placeholder="بحث بالطالب/الوصف" @input="debouncedSearch" />
        </div>
      </div>
      <div class="d-flex align-items-center gap-2 mt-3">
        <button class="btn btn-outline-primary" :disabled="loading" @click="reload">تحديث</button>
        <span class="ms-auto small" :class="liveClass" aria-live="polite">{{ liveMsg }}</span>
      </div>
      <!-- شريط مؤشرات KPIs مختصر من /summary/ -->
      <div class="mt-3">
        <div v-if="summaryLoading" class="small text-muted">تحميل الملخّص ...</div>
        <div v-else-if="summaryError" class="alert alert-warning py-1 px-2 mb-0 small">{{ summaryError }}</div>
        <div v-else class="d-flex flex-wrap gap-2 align-items-center">
          <span class="badge bg-secondary">الإجمالي: {{ summary.total }}</span>
          <span class="badge bg-danger">مفتوح: {{ summary.by_status.open }}</span>
          <span class="badge bg-warning text-dark">قيد المراجعة: {{ summary.by_status.under_review }}</span>
          <span class="badge bg-success">مغلق: {{ summary.by_status.closed }}</span>
          <span class="ms-2 small text-muted">شدة:</span>
          <span class="badge" :style="{ backgroundColor: levelColor(1), color: sevTextColor(1) }">1: {{ summary.by_severity['1'] ?? 0 }}</span>
          <span class="badge" :style="{ backgroundColor: levelColor(2), color: sevTextColor(2) }">2: {{ summary.by_severity['2'] ?? 0 }}</span>
          <span class="badge" :style="{ backgroundColor: levelColor(3), color: sevTextColor(3) }">3: {{ summary.by_severity['3'] ?? 0 }}</span>
          <span class="badge" :style="{ backgroundColor: levelColor(4), color: sevTextColor(4) }">4: {{ summary.by_severity['4'] ?? 0 }}</span>
        </div>
      </div>
    </div>

    <!-- جدول الوقائع (إظهار أكبر قدر ممكن من البيانات ذات الصلة) -->
    <div class="card p-0 table-card">
      <div class="table-responsive mb-0">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th style="width: 36px"></th>
              <th>المعرّف</th>
              <th>الطالب</th>
              <th>إجمالي مخالفات الطالب</th>
              <th>رقم الطالب</th>
              <th>الصف</th>
              <th>الجناح</th>
              <th>تاريخ الواقعة</th>
              <th>وقت الواقعة</th>
              <th>تاريخ الإنشاء</th>
              <th>الموقع</th>
              <th>رمز المخالفة</th>
              <th>فئة المخالفة</th>
              <th>شدة</th>
              <th title="هل تتطلب الواقعة إحالة إلى لجنة الانضباط المدرسية؟" aria-label="عمود يشير إلى إحالة لجنة">
                لجنة؟
              </th>
              <th>المبلِّغ</th>
              <th>الحالة</th>
              <th>إجراءات</th>
              <th>عقوبات</th>
              <th style="width:320px">عمليات</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!loading && items.length===0">
              <td :colspan="19" class="text-center text-muted py-4">لا توجد بلاغات مطابقة</td>
            </tr>
            <template v-for="it in items" :key="it.id">
              <tr>
                <td>
                  <button class="btn btn-sm btn-outline-secondary" @click="toggleExpand(it.id)" :aria-expanded="isExpanded(it.id)">
                    {{ isExpanded(it.id) ? '−' : '+' }}
                  </button>
                </td>
                <td class="text-truncate" style="max-width: 160px">{{ it.id }}</td>
                <td>{{ it.student_name || it.student_obj?.full_name || '-' }}</td>
                <td>
                  <span v-if="studentCountsLoading" class="text-muted">…</span>
                  <span v-else>{{ studentCounts[String(it.student_obj?.id || it.student)] ?? '—' }}</span>
                </td>
                <td>{{ it.student_obj?.sid || '-' }}</td>
                <td>{{ it.class_name || it.class_obj?.name || '-' }}</td>
                <td>{{ it.wing_obj?.name || '-' }}</td>
                <td>{{ fmtDate(it.occurred_at || it.created_at) }}</td>
                <td>{{ it.occurred_time || fmtTime(it.occurred_at) }}</td>
                <td>{{ fmtDate(it.created_at) }}</td>
                <td>{{ it.location || '-' }}</td>
                <td>{{ it.violation_code || it.violation_obj?.code || '-' }}</td>
                <td>{{ it.violation_category || it.violation_obj?.category || '-' }}</td>
                <td>
                  <span class="badge" :style="{ backgroundColor: levelColor(it.severity), color: sevTextColor(it.severity) }">{{ it.severity ?? '-' }}</span>
                </td>
                <td>
                  <span
                    class="badge"
                    :class="it.committee_required ? 'bg-danger' : 'bg-secondary'"
                    :title="committeeTitle(it)"
                    aria-label="مؤشر إحالة لجنة"
                  >
                    {{ it.committee_required ? 'نعم' : 'لا' }}
                  </span>
                </td>
                <td>{{ it.reporter_obj?.staff_full_name || it.reporter_name || it.reporter_obj?.full_name || it.reporter_obj?.username || '-' }}</td>
                <td><span class="badge" :class="statusClass(it.status)">{{ statusLabel(it.status) }}</span></td>
                <td>{{ it.actions_count ?? (it.actions_applied?.length || 0) }}</td>
                <td>{{ it.sanctions_count ?? (it.sanctions_applied?.length || 0) }}</td>
                <td>
                  <div class="d-flex flex-wrap gap-1">
                    <button class="btn btn-sm btn-outline-primary" :disabled="rowBusy(it.id) || !canSubmit(it)" @click="onSubmit(it)">إرسال</button>
                    <button class="btn btn-sm btn-outline-warning" :disabled="rowBusy(it.id) || !canReview(it)" @click="onReview(it)">استلام</button>
                    <button class="btn btn-sm btn-outline-info" :disabled="rowBusy(it.id) || !canNotify(it)" @click="onNotify(it)">إشعار</button>
                    <button class="btn btn-sm btn-outline-dark" :disabled="rowBusy(it.id) || !canEscalate(it)" @click="onEscalate(it)">تصعيد</button>
                    <button class="btn btn-sm btn-outline-success" :disabled="rowBusy(it.id) || !canClose(it)" @click="onClose(it)">إغلاق</button>
                    <button class="btn btn-sm btn-outline-secondary" :disabled="rowBusy(it.id) || !canAppeal(it)" @click="onAppeal(it)">تظلّم</button>
                    <button class="btn btn-sm btn-outline-secondary" :disabled="rowBusy(it.id) || !canReopen(it)" @click="onReopen(it)">إعادة فتح</button>
                    <!-- تم نقل تشكيل اللجنة إلى الباكند وفق المتطلب؛ زر الواجهة مُزال -->
                  </div>
                </td>
              </tr>
              <tr v-if="isExpanded(it.id)" class="table-light">
                <td></td>
                <td colspan="18">
                  <div class="row g-3 p-3">
                    <div class="col-md-6">
                      <h6 class="mb-2">تفاصيل المخالفة</h6>
                      <pre class="small mb-0">{{ pretty(it.violation_obj) }}</pre>
                    </div>
                    <div class="col-md-6">
                      <h6 class="mb-2">الطالب/الصف/الجناح</h6>
                      <pre class="small mb-0">{{ pretty({ student: it.student_obj, class: it.class_obj, wing: it.wing_obj }) }}</pre>
                    </div>
                    <div class="col-md-6">
                      <h6 class="mb-2">الإجراءات المطبّقة</h6>
                      <pre class="small mb-0">{{ pretty(it.actions_applied) }}</pre>
                    </div>
                    <div class="col-md-6">
                      <h6 class="mb-2">العقوبات المطبّقة</h6>
                      <pre class="small mb-0">{{ pretty(it.sanctions_applied) }}</pre>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <div v-if="loading" class="p-3 text-muted">جاري التحميل ...</div>
      <div class="d-flex align-items-center gap-2 p-2 border-top">
        <div class="small text-muted">النتائج: {{ total }}</div>
        <div class="ms-auto d-flex align-items-center gap-2">
          <button class="btn btn-sm btn-outline-secondary" :disabled="offset===0 || loading" @click="prevPage">السابق</button>
          <button class="btn btn-sm btn-outline-secondary" :disabled="offset+limit>=total || loading" @click="nextPage">التالي</button>
        </div>
      </div>
    </div>
  </section>

  <!-- نافذة منبثقة لاختيار تشكيلة اللجنة -->
  <div v-if="committeeModal.open" class="modal-backdrop" role="dialog" aria-modal="true">
    <div class="modal-card" dir="rtl">
      <div class="modal-header d-flex align-items-center">
        <h6 class="mb-0">تشكيل اللجنة للواقعة {{ committeeModal.incidentId }}</h6>
        <button class="btn-close" @click="closeCommittee" aria-label="إغلاق">×</button>
      </div>
      <div class="modal-body">
        <div v-if="committeeModal.loading" class="text-muted">جاري تحميل المرشحين والاقتراح ...</div>
        <div v-else-if="committeeModal.error" class="alert alert-warning py-1 px-2">{{ committeeModal.error }}</div>
        <div v-else>
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label">بحث عن اسم موظف</label>
              <input type="search" class="form-control" v-model.trim="committeeModal.query" placeholder="اكتب للبحث" />
            </div>
            <div class="col-md-6 col-12">
              <label class="form-label">مدير اللجنة (الرئيس)</label>
              <select class="form-select" v-model.number="committeeModal.selection.chairId">
                <option v-for="u in committeeFiltered" :key="u.id" :value="u.id">{{ bestName(u) }} ({{ u.id }})</option>
              </select>
              <small class="text-muted">يمتلك صلاحيات: جدولة واعتماد القرار.</small>
            </div>
            <div class="col-md-6 col-12">
              <label class="form-label">مقرر اللجنة</label>
              <select class="form-select" v-model.number="committeeModal.selection.recorderId">
                <option :value="0">— لا يوجد —</option>
                <option v-for="u in committeeFiltered" :key="'r'+u.id" :value="u.id">{{ bestName(u) }} ({{ u.id }})</option>
              </select>
              <small class="text-muted">مسؤول تدوين محضر الجلسة.</small>
            </div>
            <div class="col-12">
              <label class="form-label">أعضاء اللجنة (يمكن اختيار أكثر من عضو)</label>
              <select class="form-select" multiple size="6" v-model="committeeModal.selection.memberIdsStr">
                <option v-for="u in committeeFiltered" :key="'m'+u.id" :value="String(u.id)">{{ bestName(u) }} ({{ u.id }})</option>
              </select>
              <small class="text-muted">الحد الأدنى المقترح: عضوان على الأقل.</small>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-footer d-flex align-items-center">
        <div class="small text-danger" v-if="committeeValidationMsg">{{ committeeValidationMsg }}</div>
        <div class="ms-auto d-flex gap-2">
          <button class="btn btn-secondary" @click="closeCommittee">إلغاء</button>
          <button class="btn btn-primary" :disabled="!!committeeValidationMsg || committeeModal.loading" @click="confirmCommittee">تأكيد الاختيار</button>
        </div>
      </div>
    </div>
  </div>

</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import WingPageHeader from "../../../components/ui/WingPageHeader.vue";
import { tiles } from "../../../home/icon-tiles.config";
const tileMeta = computed(() => tiles.find((t) => t.to === "/wing/incidents") || { title: "وقائع الجناح", icon: "solar:shield-warning-bold-duotone", color: "#c0392b" });
import { useWingContext } from "../../../shared/composables/useWingContext";
const { selectedWingId } = useWingContext();
import { getIncidentsVisible, submitIncident, reviewIncident, addIncidentAction, addIncidentSanction, escalateIncident, notifyGuardian, closeIncident, appealIncident, reopenIncident, countIncidentsByStudent, getIncidentsSummary, getCommitteeSuggest } from "../../discipline/api";
import { useToast } from "vue-toastification";
const toast = useToast();

// فلاتر بسيطة
const from = ref<string>("");
const to = ref<string>("");
const status = ref<string>(""); // نقبل صيغ الواجهة، والخادم يقوم بالتطبيع
const q = ref<string>("");
const limit = ref(25);
const offset = ref(0);

// بيانات العرض
const loading = ref(false);
const error = ref("");
const items = ref<any[]>([]);
const total = ref(0);

// KPIs summary من /summary/
const summaryLoading = ref(false);
const summaryError = ref("");
const summary = ref<{ total: number; by_status: { open: number; under_review: number; closed: number }; by_severity: Record<string, number> }>({
  total: 0,
  by_status: { open: 0, under_review: 0, closed: 0 },
  by_severity: { "1": 0, "2": 0, "3": 0, "4": 0 }
});
async function loadSummary(){
  try{
    summaryLoading.value = true; summaryError.value = "";
    const params:any = {
      from: from.value || undefined,
      to: to.value || undefined,
      status: status.value || undefined,
    };
    const wing = selectedWingId.value; if (wing) params.wing_id = wing;
    const res = await getIncidentsSummary(params);
    summary.value = res || summary.value;
  }catch(e:any){
    summaryError.value = e?.message || 'تعذّر تحميل الملخص';
  }finally{
    summaryLoading.value = false;
  }
}

// عدّ إجمالي مخالفات الطالب (لكل طالب في الصفحة الحالية)
const studentCounts = ref<Record<string, number>>({});
const studentCountsLoading = ref(false);
const studentCountsError = ref<string>("");
async function refreshStudentCounts(){
  try{
    studentCountsLoading.value = true;
    studentCountsError.value = "";
    const ids = Array.from(new Set(
      (items.value || [])
        .map((it:any) => (it?.student_obj?.id ?? it?.student))
        .filter((v:any) => v !== undefined && v !== null)
        .map((v:any) => String(v))
    ));
    if (ids.length === 0){ studentCounts.value = {}; return; }
    const res = await countIncidentsByStudent({ student_ids: ids.join(',') });
    studentCounts.value = res || {};
  }catch(e:any){
    studentCountsError.value = e?.message || 'تعذّر تحميل عدادات الطلاب';
  }finally{
    studentCountsLoading.value = false;
  }
}

// الصفوف الموسّعة
const expanded = ref<Set<string>>(new Set());
function isExpanded(id: string){ return expanded.value.has(id); }
function toggleExpand(id: string){ if (expanded.value.has(id)) { expanded.value.delete(id); } else { expanded.value.add(id); } expanded.value = new Set(expanded.value); }

const liveMsg = ref("");
const liveClass = computed(() => (liveMsg.value.includes("فشل") ? "text-danger" : "text-success"));

function applyFilters(){ offset.value = 0; reload(); }
let timer: any = null;
function debouncedSearch(){ clearTimeout(timer); timer = setTimeout(()=>applyFilters(), 400); }

async function reload(){
  loading.value = true; error.value = ""; items.value = []; total.value = 0;
  try{
    const params:any = {
      from: from.value || undefined,
      to: to.value || undefined,
      status: status.value || undefined,
      q: q.value || undefined,
      limit: limit.value,
      offset: offset.value,
      expand: 'all',
    };
    const wing = selectedWingId.value; if (wing) params.wing_id = wing;
    const res = await getIncidentsVisible(params);
    const arr = Array.isArray((res as any)?.items) ? (res as any).items : [];
    items.value = arr;
    total.value = typeof (res as any)?.total === 'number' ? (res as any).total : arr.length;
    liveMsg.value = `تم التحديث (${from.value || 'بلا حد'} → ${to.value || 'بلا حد'})`;
    // حدّث عدادات الطلاب للصفحة الحالية دون إبطاء استجابة الجدول
    refreshStudentCounts();
    // حمّل ملخص KPIs المطابق لنفس الفلاتر
    loadSummary();
  }catch(e:any){
    error.value = e?.message || 'تعذّر تحميل الوقائع';
    liveMsg.value = 'فشل التحديث';
  }finally{
    loading.value = false;
  }
}

function prevPage(){ if(offset.value>0){ offset.value = Math.max(0, offset.value - limit.value); reload(); } }
function nextPage(){ if(offset.value + limit.value < total.value){ offset.value += limit.value; reload(); } }

function fmtDate(s?: string){ if(!s) return '—'; if (s.length===10) return s; try{ const d=new Date(s); const y=d.getFullYear(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${dd}`; }catch{ return s; } }
function fmtTime(s?: string){ if(!s) return ''; try{ const d=new Date(s); const hh=String(d.getHours()).padStart(2,'0'); const mm=String(d.getMinutes()).padStart(2,'0'); return `${hh}:${mm}`; }catch{ return ''; } }
function statusLabel(v: string){ return v==='open'?'مفتوح': v==='under_review'?'قيد المراجعة': v==='closed'?'مغلق': v==='in_progress'?'قيد المعالجة': v==='resolved'?'تم الحل': v==='archived'?'مؤرشفة': v; }
function statusClass(v: string){ return v==='open'?'bg-danger': v==='under_review' || v==='in_progress' ? 'bg-warning text-dark' : 'bg-success'; }
function levelColor(sev?: number){ const s = Number(sev||1); return s===1?'#2e7d32': s===2?'#f9a825': s===3?'#fb8c00':'#c62828'; }
function sevTextColor(sev?: number){ const s = Number(sev||1); return s>=3 ? '#fff' : '#000'; }
function pretty(v:any){ try{ return JSON.stringify(v, null, 2); }catch{ return String(v); } }

// تفسير شارة "لجنة؟" للمستخدم: توضح لماذا قد تكون مفعّلة
function committeeTitle(it:any){
  try{
    if (!it?.committee_required) return 'لا تتطلب هذه الواقعة إحالة إلى لجنة.';
    const reasons: string[] = [];
    const sev = Number(it?.severity || 0);
    const requiresFromCatalog = !!it?.violation_obj?.requires_committee;
    const escalated = !!it?.escalated_due_to_repeat;
    if (requiresFromCatalog) reasons.push('متطلب من كتالوج المخالفات لهذه الحالة');
    if (sev >= 3) reasons.push('شدة المخالفة مرتفعة (3 أو 4)');
    if (escalated) reasons.push('تم التصعيد بسبب التكرار/قرار المراجع');
    const joined = reasons.length ? ('الأسباب: ' + reasons.join('، ')) : 'مفعّلة بناءً على سياسة الشدة/التصعيد.';
    return 'تحتاج الواقعة إلى عرض على لجنة الانضباط المدرسية. ' + joined;
  }catch{
    return 'تحتاج الواقعة إلى عرض على لجنة الانضباط المدرسية.';
  }
}

onMounted(()=>{ reload(); loadSummary(); });
watch(()=>selectedWingId.value, ()=>{ reload(); loadSummary(); });

// إدارة حالة الانشغال لكل صف
const busy: any = ref<Record<string, boolean>>({});
function rowBusy(id: string){ return !!busy.value[id]; }
function setBusy(id: string, v: boolean){ busy.value = { ...busy.value, [id]: v }; }

// قواعد السماحية البسيطة حسب الحالة (الخادم يتحقق من الصلاحيات فعليًا)
function canSubmit(it:any){ return it.status === 'open'; }
function canReview(it:any){ return it.status !== 'closed'; }
function canNotify(it:any){ return it.status === 'open' || it.status === 'under_review'; }
function canEscalate(it:any){ return it.status === 'under_review'; }
function canClose(it:any){ return it.status === 'open' || it.status === 'under_review'; }
function canAppeal(it:any){ return it.status === 'closed'; }
function canReopen(it:any){ return it.status === 'closed'; }

function updateRow(id: string, updated: any){
  if (!updated) return;
  const idx = items.value.findIndex((x) => x.id === id);
  if (idx >= 0) {
    items.value[idx] = { ...items.value[idx], ...updated };
    // إعادة حساب عدادات الإجراءات/العقوبات إن توفرت القوائم
    const it = items.value[idx];
    if (Array.isArray(it.actions_applied)) it.actions_count = it.actions_applied.length;
    if (Array.isArray(it.sanctions_applied)) it.sanctions_count = it.sanctions_applied.length;
    items.value = items.value.slice();
  }
}

function extractIncident(res:any){
  if (!res) return null;
  if (res.incident) return res.incident;
  // في بعض النهايات قد تُعاد بيانات الواقعة مباشرةً
  if (res.id && res.status && res.student) return res;
  return null;
}

async function onSubmit(it:any){
  if (!canSubmit(it)) return;
  setBusy(it.id, true);
  try{
    const res = await submitIncident(it.id);
    const inc = extractIncident(res);
    if (inc) updateRow(it.id, inc); else await reload();
    toast.success('تم إرسال الواقعة للمراجعة');
  }catch(e:any){ toast.error(e?.message || 'تعذّر إرسال الواقعة'); }
  finally{ setBusy(it.id, false); }
}

async function onReview(it:any){
  if (!canReview(it)) return;
  setBusy(it.id, true);
  try{
    const res = await reviewIncident(it.id);
    const inc = extractIncident(res);
    if (inc) updateRow(it.id, inc); else await reload();
    toast.success('تم استلام الواقعة للمراجعة');
  }catch(e:any){ toast.error(e?.message || 'تعذّر تنفيذ الاستلام'); }
  finally{ setBusy(it.id, false); }
}

async function onNotify(it:any){
  if (!canNotify(it)) return;
  const channel = prompt('قناة الإشعار (مثال: internal / sms / call):','internal') || 'internal';
  const note = prompt('ملاحظة للإشعار (اختياري):','') || '';
  setBusy(it.id, true);
  try{
    const res = await notifyGuardian(it.id, { channel, note });
    const inc = extractIncident(res);
    if (inc) updateRow(it.id, inc); else await reload();
    toast.success('تم إشعار ولي الأمر');
  }catch(e:any){ toast.error(e?.message || 'تعذّر إشعار ولي الأمر'); }
  finally{ setBusy(it.id, false); }
}

async function onEscalate(it:any){
  if (!canEscalate(it)) return;
  if (!confirm('هل تريد تصعيد الواقعة؟')) return;
  setBusy(it.id, true);
  try{
    const res = await escalateIncident(it.id);
    const inc = extractIncident(res);
    if (inc) updateRow(it.id, inc); else await reload();
    toast.success('تم التصعيد');
  }catch(e:any){ toast.error(e?.message || 'تعذّر التصعيد'); }
  finally{ setBusy(it.id, false); }
}

async function onClose(it:any){
  if (!canClose(it)) return;
  if (!confirm('إغلاق الواقعة؟ سيتم نقلها إلى حالة مغلقة.')) return;
  setBusy(it.id, true);
  try{
    const res = await closeIncident(it.id);
    const inc = extractIncident(res);
    if (inc) updateRow(it.id, inc); else await reload();
    toast.success('تم إغلاق الواقعة');
  }catch(e:any){ toast.error(e?.message || 'تعذّر الإغلاق'); }
  finally{ setBusy(it.id, false); }
}

async function onAppeal(it:any){
  if (!canAppeal(it)) return;
  const reason = prompt('سبب التظلّم (اختياري):','') || '';
  setBusy(it.id, true);
  try{
    const res = await appealIncident(it.id, { reason });
    const inc = extractIncident(res);
    if (inc) updateRow(it.id, inc); else await reload();
    toast.success('تم تقديم التظلّم');
  }catch(e:any){ toast.error(e?.message || 'تعذّر تقديم التظلّم'); }
  finally{ setBusy(it.id, false); }
}

async function onReopen(it:any){
  if (!canReopen(it)) return;
  const note = prompt('ملاحظة إعادة الفتح (اختياري):','') || '';
  setBusy(it.id, true);
  try{
    const res = await reopenIncident(it.id, { note });
    const inc = extractIncident(res);
    if (inc) updateRow(it.id, inc); else await reload();
    toast.success('تمت إعادة فتح الواقعة');
  }catch(e:any){ toast.error(e?.message || 'تعذّر إعادة الفتح'); }
  finally{ setBusy(it.id, false); }
}

// ------------------- تشكيل اللجنة (قوائم منسدلة) -------------------
type CommitteeUser = { id: number; username?: string; full_name?: string; staff_full_name?: string };
const committeeModal = ref({
  open: false,
  incidentId: '' as string,
  loading: false,
  error: '' as string,
  candidates: [] as CommitteeUser[],
  query: '' as string,
  selection: {
    chairId: 0,
    memberIdsStr: [] as string[], // نستخدم سلاسل لتعمل مع v-model الخاص بـ multiple
    recorderId: 0,
  },
});

const committeeFiltered = computed(() => {
  const q = (committeeModal.value.query || '').trim().toLowerCase();
  let list = committeeModal.value.candidates || [];
  if (!q) return list;
  return list.filter((u) => {
    const name = String(u.staff_full_name || u.full_name || u.username || '').toLowerCase();
    return name.includes(q) || String(u.id).includes(q);
  });
});

function bestName(u: CommitteeUser): string {
  return String(u.staff_full_name || u.full_name || u.username || '').trim() || `#${u.id}`;
}

const committeeValidationMsg = computed(() => {
  const sel = committeeModal.value.selection;
  const chair = sel.chairId;
  const recorder = sel.recorderId;
  const members = (sel.memberIdsStr || []).map((s) => Number(s));
  if (members.length < 2) return 'يجب اختيار عضوين على الأقل.';
  // منع التكرار بين الأدوار
  const set = new Set<number>(members);
  if (chair && set.has(chair)) return 'لا يمكن أن يكون الرئيس ضمن الأعضاء.';
  if (recorder && set.has(recorder)) return 'لا يمكن أن يكون المقرر ضمن الأعضاء.';
  if (chair && recorder && chair === recorder) return 'لا يمكن أن يكون الرئيس هو نفسه المقرر.';
  return '';
});

async function openCommittee(it:any){
  committeeModal.value.open = true;
  committeeModal.value.incidentId = it.id;
  committeeModal.value.loading = true;
  committeeModal.value.error = '';
  committeeModal.value.candidates = [];
  committeeModal.value.query = '';
  committeeModal.value.selection = { chairId: 0, memberIdsStr: [], recorderId: 0 };
  try{
    const res = await getCommitteeSuggest(it.id, { member_count: 2 });
    const cands = Array.isArray((res as any)?.candidates) ? (res as any).candidates : [];
    committeeModal.value.candidates = cands as CommitteeUser[];
    // تعبئة مبدئية من المقترح
    const panel = (res as any)?.panel || {};
    if (panel?.chair?.id) committeeModal.value.selection.chairId = Number(panel.chair.id);
    if (Array.isArray(panel?.members)) committeeModal.value.selection.memberIdsStr = panel.members.map((m:any)=> String(m.id));
    if (panel?.recorder?.id) committeeModal.value.selection.recorderId = Number(panel.recorder.id);
  }catch(e:any){
    committeeModal.value.error = e?.message || 'تعذّر تحميل الاقتراح.';
  }finally{
    committeeModal.value.loading = false;
  }
}

function closeCommittee(){
  committeeModal.value.open = false;
}

function confirmCommittee(){
  if (committeeValidationMsg.value) return;
  const sel = committeeModal.value.selection;
  const payload = {
    chair_id: sel.chairId || null,
    member_ids: (sel.memberIdsStr || []).map((s)=> Number(s)),
    recorder_id: sel.recorderId || null,
  };
  // لا يوجد حفظ backend حتى الآن؛ نعرض تأكيدًا ونغلق.
  toast.success('تم اختيار تشكيل اللجنة (غير محفوظ — للعرض فقط).');
  console.debug('Committee selection for', committeeModal.value.incidentId, payload);
  closeCommittee();
}
</script>

<style scoped>
.table-card { overflow: hidden; }
.text-success { color: #2e7d32 !important; }
.text-danger { color: #c62828 !important; }
.table pre { background: #fff; border: 1px solid #eee; padding: 8px; border-radius: 6px; max-height: 220px; overflow: auto; }
/* Modal styles */
.modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 1050; }
.modal-card { width: min(860px, 96vw); background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.25); }
.modal-header { padding: 12px 16px; border-bottom: 1px solid #eee; }
.modal-body { padding: 16px; max-height: 70vh; overflow: auto; }
.modal-footer { padding: 12px 16px; border-top: 1px solid #eee; }
.btn-close { margin-inline-start: auto; border: none; background: transparent; font-size: 20px; line-height: 1; cursor: pointer; }
</style>
