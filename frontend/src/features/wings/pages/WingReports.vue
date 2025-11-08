<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <!-- Header bar (unified) -->
    <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" />

        <!-- Print-only standardized header -->
        <PrintPageHeader
          :title="`تقارير الجناح — جناح ${selectedWingId || '-'}`"
          :meta-lines="[
            `الفترة: ${from} → ${to}`,
            `الصف: ${classId ? ('#'+classId) : 'كل الصفوف'}`
          ]"
        />

    <!-- Tools card: common filters (hidden in print) -->
    <div class="card p-3 no-print">
      <div class="row g-3 align-items-end">
        <div class="col-md-3 col-12">
          <label for="rep-from" class="form-label">من</label>
          <input id="rep-from" type="date" class="form-control" v-model="from" />
        </div>
        <div class="col-md-3 col-12">
          <label for="rep-to" class="form-label">إلى</label>
          <input id="rep-to" type="date" class="form-control" v-model="to" />
        </div>
        <div class="col-md-3 col-12">
          <label for="rep-class" class="form-label">الصف</label>
          <select id="rep-class" class="form-select" v-model.number="classId">
            <option :value="null">كل الصفوف</option>
            <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <div class="form-text">تعرض القائمة صفوف الجناح المحدد فقط.</div>
        </div>
        <div class="col-md-3 col-12 d-flex align-items-end gap-2">
          <button class="btn btn-outline-primary" @click="refresh">تحديث الروابط</button>
          <span class="small ms-auto text-muted" aria-live="polite">{{ hint }}</span>
        </div>
      </div>
    </div>

    <!-- Reports cards -->
    <div class="row g-3">
      <div class="col-xl-4 col-md-6 col-12">
        <div class="card p-3 h-100">
          <h6 class="fw-bold mb-2 d-flex align-items-center gap-2">
            <Icon icon="solar:users-group-rounded-bold-duotone" />
            قائمة الطلبة
          </h6>
          <p class="text-muted small mb-3">قائمة طلبة الجناح/الصف المحدد لاستخدامات الاتصال.</p>
          <div class="d-flex gap-2 flex-wrap">
            <a class="btn btn-outline-success" :href="studentsCsvHref" target="_blank" rel="noopener">تنزيل CSV</a>
            <button class="btn btn-outline-primary" type="button" @click="exportStudentsWord">تنزيل Word</button>
          </div>
        </div>
      </div>
      <div class="col-xl-4 col-md-6 col-12">
        <div class="card p-3 h-100">
          <h6 class="fw-bold mb-2 d-flex align-items-center gap-2">
            <Icon icon="solar:calendar-bold-duotone" />
            غيابات اليوم
          </h6>
          <p class="text-muted small mb-3">تقرير غيابات اليوم على نطاق الجناح/الصف.</p>
          <div class="d-flex gap-2 flex-wrap">
            <a class="btn btn-outline-success" :href="dailyAbsCsvHref" target="_blank" rel="noopener">تنزيل CSV</a>
            <a class="btn btn-outline-primary" :href="dailyAbsWordHref" target="_blank" rel="noopener">تنزيل Word</a>
          </div>
        </div>
      </div>
      <div class="col-xl-4 col-md-6 col-12">
        <div class="card p-3 h-100">
          <h6 class="fw-bold mb-2 d-flex align-items-center gap-2">
            <Icon icon="solar:checklist-minimalistic-bold-duotone" />
            حصص مُدخلة
          </h6>
          <p class="text-muted small mb-3">ما تم إدخاله من حصص حسب اليوم المحدد.</p>
          <div class="d-flex gap-2 flex-wrap">
            <a class="btn btn-outline-success" :href="enteredCsvHref" target="_blank" rel="noopener">تنزيل CSV</a>
            <a class="btn btn-outline-primary" :href="enteredWordHref" target="_blank" rel="noopener">تنزيل Word</a>
          </div>
        </div>
      </div>
      <div class="col-xl-4 col-md-6 col-12">
        <div class="card p-3 h-100">
          <h6 class="fw-bold mb-2 d-flex align-items-center gap-2">
            <Icon icon="solar:shield-warning-bold-duotone" />
            حصص بلا إدخال
          </h6>
          <p class="text-muted small mb-3">الحصص غير المُدخلة لليوم المحدد.</p>
          <div class="d-flex gap-2 flex-wrap">
            <a class="btn btn-outline-success" :href="missingCsvHref" target="_blank" rel="noopener">تنزيل CSV</a>
            <a class="btn btn-outline-primary" :href="missingWordHref" target="_blank" rel="noopener">تنزيل Word</a>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { Icon } from "@iconify/vue";
import { computed, onMounted, ref, watch } from "vue";
import WingPageHeader from "../../../components/ui/WingPageHeader.vue";
import { tiles } from "../../../home/icon-tiles.config";
import PrintPageHeader from "../../../components/ui/PrintPageHeader.vue";
const tileMeta = computed(() => tiles.find((t) => t.to === "/wing/reports") || { title: "تقارير", icon: "solar:graph-new-bold-duotone", color: "rgb(26, 188, 156)" });
import { useWingContext } from "../../../shared/composables/useWingContext";
const { selectedWingId } = useWingContext();
import { getWingClasses } from "../../../shared/api/client";
import { backendUrl } from "../../../shared/config";
import { downloadWingStudentsWord } from "../../../shared/api/client";

const from = ref(isoToday());
const to = ref(isoToday());
const classId = ref<number|null>(null);
const classes = ref<{id:number; name:string}[]>([]);
const hint = ref("");

async function loadClasses(){
  try{
    const params:any = {}; const wing = selectedWingId.value; if (wing) params.wing_id = wing;
    const res = await getWingClasses(params);
    classes.value = (res.items||[]).map((c:any)=>({id:c.id, name:c.name||`#${c.id}`}));
  }catch{ }
}

function compose(url: string, params: Record<string, any>){
  const usp = new URLSearchParams();
  for (const [k,v] of Object.entries(params)){
    if (v === undefined || v === null || v === "") continue;
    usp.set(k, String(v));
  }
  return backendUrl(`/api/v1${url}?${usp.toString()}`);
}

const studentsCsvHref = computed(()=> compose("/wing/students/export/", { wing_id: selectedWingId.value || undefined, class_id: classId.value || undefined }));
const studentsWordHref = computed(()=> compose("/wing/students/export.docx/", { wing_id: selectedWingId.value || undefined, class_id: classId.value || undefined }));
const dailyAbsCsvHref = computed(()=> compose("/wing/daily-absences/export/", { date: to.value, wing_id: selectedWingId.value || undefined, class_id: classId.value || undefined }));
const dailyAbsWordHref = computed(()=> compose("/wing/daily-absences/export.docx/", { date: to.value, wing_id: selectedWingId.value || undefined, class_id: classId.value || undefined }));
const enteredCsvHref = computed(()=> compose("/wing/entered/export/", { date: to.value, wing_id: selectedWingId.value || undefined, class_id: classId.value || undefined }));
const enteredWordHref = computed(()=> compose("/wing/entered/export.docx/", { date: to.value, wing_id: selectedWingId.value || undefined, class_id: classId.value || undefined }));
const missingCsvHref = computed(()=> compose("/wing/missing/export/", { date: to.value, wing_id: selectedWingId.value || undefined, class_id: classId.value || undefined }));
const missingWordHref = computed(()=> compose("/wing/missing/export.docx/", { date: to.value, wing_id: selectedWingId.value || undefined, class_id: classId.value || undefined }));

function refresh(){ hint.value = `تم تحديث الروابط (${fmtDate(from.value)} → ${fmtDate(to.value)})`; }

onMounted(async()=>{ await loadClasses(); refresh(); });
watch(()=>selectedWingId.value, async()=>{ await loadClasses(); refresh(); });

function isoToday(){ const d=new Date(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); return `${d.getFullYear()}-${m}-${dd}`; }
function fmtDate(s?: string){ if(!s) return '—'; if(s.length===10) return s; try{ const d=new Date(s); const y=d.getFullYear(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${dd}`; }catch{ return s; } }
</script>
<style scoped>
</style>
