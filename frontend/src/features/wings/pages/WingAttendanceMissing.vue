<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <!-- Header bar (unified) -->
    <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" />

    <!-- Tools card -->
    <div class="card p-3">
      <div class="row g-3 align-items-end">
        <div class="col-sm-3 col-12">
          <label for="missing-date" class="form-label">التاريخ</label>
          <input id="missing-date" type="date" class="form-control" v-model="date" @change="reload" />
        </div>
        <div class="col-sm-4 col-12">
          <label for="missing-class" class="form-label">الصف</label>
          <select id="missing-class" class="form-select" v-model.number="classId" @change="reload">
            <option :value="null">كل الصفوف</option>
            <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <div class="form-text">تعرض القائمة صفوف الجناح المحدد فقط.</div>
        </div>
        <div class="col-sm-5 col-12 d-flex gap-2 align-items-end">
          <button ref="refreshBtn" class="btn btn-outline-primary" :disabled="loading" @click="reload">تحديث</button>
          <a v-if="csvEnabled" class="btn btn-outline-success" :href="csvHref" target="_blank" rel="noopener">تصدير CSV</a>
          <a v-if="csvEnabled" class="btn btn-outline-primary" :href="wordHref" target="_blank" rel="noopener">تصدير Word</a>
          <span class="small ms-auto" :class="liveClass" aria-live="polite">{{ liveMsg }}</span>
        </div>
      </div>
      <div v-if="error" class="alert alert-danger mt-2" role="alert">{{ error }}</div>
    </div>

    <!-- Table card -->
    <div class="card p-0 table-card">
      <div class="table-responsive mb-0">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>الصف</th>
              <th>الحصة</th>
              <th>المادة</th>
              <th>المعلم</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!loading && visibleItems.length===0">
              <td :colspan="4" class="text-center text-muted py-4">لا توجد حصص بلا إدخال</td>
            </tr>
            <tr v-for="it in visibleItems" :key="it.class_id + '-' + it.period_number">
              <td>{{ it.class_name || '-' }}</td>
              <td>{{ it.period_number }}</td>
              <td>{{ it.subject_name || '-' }}</td>
              <td>{{ it.teacher_name || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="loading" class="p-3 text-muted">جاري التحميل ...</div>
      <div class="d-flex align-items-center gap-2 p-2 border-top">
        <div class="small text-muted">النتيجة: {{ visibleItems.length }} من {{ items.length }}</div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { Icon } from "@iconify/vue";
import { tiles } from "../../../home/icon-tiles.config";
const tileMeta = computed(() => tiles.find((t) => t.to === "/wing/attendance/missing") || { title: "حصص بلا إدخال", icon: "solar:shield-warning-bold-duotone", color: "#f39c12" });
import WingPageHeader from "../../../components/ui/WingPageHeader.vue";
import { useWingContext } from "../../../shared/composables/useWingContext";
const { selectedWingId } = useWingContext();
import { useWingPrefs } from "../../../shared/composables/useWingPrefs";
const { enable_csv_buttons } = useWingPrefs();
import { getWingClasses, getWingMissing } from "../../../shared/api/client";
import { backendUrl } from "../../../shared/config";

const csvEnabled = computed(()=> !!enable_csv_buttons.value);
const date = ref(isoToday());
const classId = ref<number | null>(null);
const loading = ref(false);
const error = ref("");
const items = ref<any[]>([]);
const classes = ref<{id:number; name:string}[]>([]);
const liveMsg = ref("");
const liveClass = computed(()=> liveMsg.value.includes("فشل")?"text-danger":"text-success");

const visibleItems = computed(()=> classId.value ? items.value.filter(x=>x.class_id===classId.value) : items.value);

const csvHref = computed(()=>{
  const params = new URLSearchParams();
  if (date.value) params.set("date", date.value);
  const wing = selectedWingId.value; if (wing) params.set("wing_id", String(wing));
  if (classId.value) params.set("class_id", String(classId.value));
  params.set("format","csv");
  return backendUrl(`/api/v1/wing/missing/?${params.toString()}`);
});
const wordHref = computed(()=>{
  const params = new URLSearchParams();
  if (date.value) params.set("date", date.value);
  const wing = selectedWingId.value; if (wing) params.set("wing_id", String(wing));
  if (classId.value) params.set("class_id", String(classId.value));
  return backendUrl(`/api/v1/wing/missing/export.docx/?${params.toString()}`);
});

async function loadClasses(){
  try{
    const params:any = {}; const wing = selectedWingId.value; if (wing) params.wing_id = wing;
    const res = await getWingClasses(params);
    classes.value = (res.items||[]).map((c:any)=>({id:c.id,name:c.name||`#${c.id}`}));
  }catch{ /* ignore */ }
}

async function reload(){
  loading.value = true; error.value = ""; liveMsg.value = "";
  try{
    const wing = selectedWingId.value || undefined;
    const res = await getWingMissing({ date: date.value, wing_id: wing as any });
    items.value = res.items || [];
    liveMsg.value = `تم التحديث (${fmt(date.value)})`;
  }catch(e:any){
    error.value = e?.message || "تعذّر تحميل البيانات";
    liveMsg.value = "فشل التحديث";
  }finally{
    loading.value = false;
  }
}

onMounted(async()=>{ await loadClasses(); await reload(); });
watch(()=>selectedWingId.value, async()=>{ await loadClasses(); await reload(); });

function isoToday(){ const d=new Date(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); return `${d.getFullYear()}-${m}-${dd}`; }
function fmt(s:string){ return s?.length===10?s: s; }
</script>
<style scoped>
.table-card { overflow: hidden; }
</style>
