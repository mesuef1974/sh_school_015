<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <!-- Header bar (unified) -->
    <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" />

    <!-- Tools card: filters and actions -->
    <div class="card p-3">
      <div class="row g-3 align-items-end">
        <div class="col-md-3 col-12">
          <label for="from" class="form-label">من</label>
          <input id="from" type="date" class="form-control" v-model="from" @change="onFilterChange" />
        </div>
        <div class="col-md-3 col-12">
          <label for="to" class="form-label">إلى</label>
          <input id="to" type="date" class="form-control" v-model="to" @change="onFilterChange" />
        </div>
        <div class="col-md-3 col-12">
          <label for="cls" class="form-label">الصف</label>
          <select id="cls" class="form-select" v-model.number="classId" @change="onFilterChange">
            <option :value="null">كل الصفوف</option>
            <option v-for="c in classes" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <div class="form-text">مُقيّد بجناح العنوان.</div>
        </div>
        <div class="col-md-3 col-12">
          <label for="status" class="form-label">الحالة</label>
          <select id="status" class="form-select" v-model="status" @change="onFilterChange">
            <option value="">الكل</option>
            <option value="open">مفتوح</option>
            <option value="in_progress">قيد المعالجة</option>
            <option value="resolved">تم الحل</option>
            <option value="archived">مؤرشفة</option>
          </select>
        </div>
        <div class="col-12">
          <label for="q" class="form-label">بحث</label>
          <input id="q" type="search" class="form-control" v-model.trim="q" placeholder="بحث بالطالب/الوصف" @input="onSearchInput" />
        </div>
      </div>
      <div class="d-flex align-items-center gap-2 mt-2">
        <button ref="refreshBtn" class="btn btn-outline-primary" :disabled="loading" @click="reload">تحديث</button>
        <button class="btn btn-success" :disabled="!canAct || selectedIds.size===0" @click="bulkAction('ack')">اعتماد استلام</button>
        <button class="btn btn-outline-warning" :disabled="!canAct || selectedIds.size===0" @click="bulkAction('resolve')">تعيين كمحلول</button>
        <button class="btn btn-outline-secondary" :disabled="!canAct || selectedIds.size===0" @click="bulkAction('archive')">أرشفة</button>
        <span class="ms-auto small" :class="liveClass" aria-live="polite">{{ liveMsg }}</span>
      </div>
      <div v-if="error" class="alert alert-danger mt-2" role="alert">{{ error }}</div>
    </div>

    <!-- Table card -->
    <div class="card p-0 table-card">
      <div class="table-responsive mb-0">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th style="width:42px"><input class="form-check-input" type="checkbox" :checked="allVisibleSelected" @change="toggleSelectAll($event)" /></th>
              <th>الطالب</th>
              <th>الصف</th>
              <th>التاريخ</th>
              <th>النوع</th>
              <th>الوصف</th>
              <th>الحالة</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!loading && items.length===0">
              <td :colspan="7" class="text-center text-muted py-4">لا توجد بلاغات مطابقة</td>
            </tr>
            <tr v-for="it in items" :key="it.id">
              <td><input class="form-check-input" type="checkbox" :checked="selectedIds.has(it.id)" @change="toggleSelect(it.id,$event)" /></td>
              <td>{{ it.student_name || '-' }}</td>
              <td>{{ it.class_name || '-' }}</td>
              <td>{{ fmtDate(it.created_at) }}</td>
              <td>{{ it.type || '-' }}</td>
              <td>{{ it.description || it.title || '-' }}</td>
              <td><span class="badge bg-secondary">{{ it.status || '—' }}</span></td>
            </tr>
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
</template>
<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import WingPageHeader from "../../../components/ui/WingPageHeader.vue";
import { tiles } from "../../../home/icon-tiles.config";
const tileMeta = computed(() => tiles.find((t) => t.to === "/wing/incidents") || { title: "البلاغات", icon: "solar:shield-warning-bold-duotone", color: "#c0392b" });
import { useWingContext } from "../../../shared/composables/useWingContext";
const { selectedWingId, hasWingRole, isSuper } = useWingContext();
import { getWingClasses } from "../../../shared/api/client";

const canAct = computed(()=> hasWingRole.value || isSuper.value);

// Filters
const from = ref(isoToday());
const to = ref(isoToday());
const classId = ref<number|null>(null);
const status = ref<string>("");
const q = ref<string>("");
const limit = ref(25);
const offset = ref(0);

// Data
const loading = ref(false);
const error = ref("");
const items = ref<any[]>([]);
const total = ref(0);
const selectedIds = reactive(new Set<number>());
const allVisibleSelected = computed(()=> items.value.length>0 && items.value.every(x=>selectedIds.has(x.id)));

const classes = ref<{id:number; name:string}[]>([]);
async function loadClasses(){
  try{
    const params:any = {}; const wing = selectedWingId.value; if (wing) params.wing_id = wing;
    const res = await getWingClasses(params);
    classes.value = (res.items||[]).map((c:any)=>({id:c.id, name:c.name||`#${c.id}`}));
  }catch{ }
}

// Placeholder reload (await backend wiring)
async function reload(){
  loading.value = true; error.value = ""; items.value = []; total.value=0; selectedIds.clear();
  try{
    await delay(200);
    items.value = [];
    total.value = 0;
    liveMsg.value = `تم التحديث (${from.value} → ${to.value})`;
  }catch(e:any){
    error.value = e?.message || "تعذّر تحميل البلاغات";
    liveMsg.value = "فشل التحديث";
  }finally{
    loading.value = false;
  }
}

async function bulkAction(kind: 'ack'|'resolve'|'archive'){
  if (!canAct.value || selectedIds.size===0) return;
  try{
    liveMsg.value = `جارٍ تنفيذ: ${kind} ...`;
    await delay(200);
    liveMsg.value = `تم تنفيذ ${kind} على ${selectedIds.size} عنصر`;
    await reload();
  }catch{
    liveMsg.value = `فشل تنفيذ العملية: ${kind}`;
  }
}

function onFilterChange(){ offset.value = 0; reload(); }
let searchTimer:any = null;
function onSearchInput(){ clearTimeout(searchTimer); searchTimer = setTimeout(()=>{ offset.value=0; reload(); }, 400); }
function prevPage(){ if(offset.value>0){ offset.value = Math.max(0, offset.value - limit.value); reload(); } }
function nextPage(){ offset.value += limit.value; reload(); }

function toggleSelect(id:number, ev: Event){ const checked = (ev.target as HTMLInputElement).checked; if(checked) selectedIds.add(id); else selectedIds.delete(id); }
function toggleSelectAll(ev: Event){ const checked = (ev.target as HTMLInputElement).checked; if(checked){ items.value.forEach(it=>selectedIds.add(it.id)); } else { selectedIds.clear(); } }

const liveMsg = ref("");
const liveClass = computed(()=> liveMsg.value.includes("فشل")?"text-danger":"text-success");
const refreshBtn = ref<HTMLButtonElement|null>(null);

onMounted(async()=>{ await loadClasses(); await reload(); });
watch(()=>selectedWingId.value, async()=>{ await loadClasses(); await reload(); });

function isoToday(){ const d=new Date(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); return `${d.getFullYear()}-${m}-${dd}`; }
function fmtDate(s?: string){ if(!s) return '—'; if (s.length===10) return s; try{ const d=new Date(s); const y=d.getFullYear(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${dd}`; }catch{ return s; } }
function delay(ms:number){ return new Promise(res=>setTimeout(res, ms)); }
</script>
<style scoped>
.table-card { overflow: hidden; }
</style>