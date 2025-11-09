<template>
  <section class="container py-3" dir="rtl">
    <div class="page-stack">
      <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" :color="tileMeta.color" :subtitle="tileMeta.subtitle">
        <template #actions>
          <div class="d-flex align-items-center gap-2">
            <select v-model="status" class="form-select form-select-sm" style="width:auto" @change="reload">
              <option value="">كل الحالات</option>
              <option value="open">مسودة</option>
              <option value="under_review">قيد المراجعة</option>
              <option value="closed">مغلقة</option>
            </select>
            <input v-model.trim="q" @input="onSearchInput" type="search" class="form-control form-control-sm" style="width:260px" placeholder="بحث" />
            <button class="btn btn-sm btn-outline-dark" :disabled="loading" @click="reload">تحديث</button>
          </div>
        </template>
      </WingPageHeader>

      <div class="row g-3">
        <div class="col-lg-4 col-12">
          <div class="kanban-col">
            <div class="kanban-head bg-info text-white">مسودة ({{ counts.open }})</div>
            <div class="kanban-body">
              <IncidentCardMini v-for="it in columns.open" :key="it.id" :it="it" />
              <div v-if="!loading && columns.open.length===0" class="text-muted small p-3">— لا عناصر —</div>
            </div>
          </div>
        </div>
        <div class="col-lg-4 col-12">
          <div class="kanban-col">
            <div class="kanban-head bg-warning">قيد المراجعة ({{ counts.under_review }})</div>
            <div class="kanban-body">
              <IncidentCardMini v-for="it in columns.under_review" :key="it.id" :it="it" />
              <div v-if="!loading && columns.under_review.length===0" class="text-muted small p-3">— لا عناصر —</div>
            </div>
          </div>
        </div>
        <div class="col-lg-4 col-12">
          <div class="kanban-col">
            <div class="kanban-head bg-secondary text-white">مغلقة ({{ counts.closed }})</div>
            <div class="kanban-body">
              <IncidentCardMini v-for="it in columns.closed" :key="it.id" :it="it" />
              <div v-if="!loading && columns.closed.length===0" class="text-muted small p-3">— لا عناصر —</div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="loading" class="text-muted">جاري التحميل …</div>
      <div v-if="!loading && error" class="text-danger">{{ error }}</div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { computed, ref } from 'vue';
import WingPageHeader from '../../../components/ui/WingPageHeader.vue';
import { tiles } from '../../../home/icon-tiles.config';
import { getKanban } from '../api';
import IncidentCardMini from './partials/IncidentCardMini.vue';

const tileMeta = computed(()=> tiles.find(t=> t.to === '/discipline/kanban' || t.to === '/wing/incidents') || ({ title: 'لوحة الانضباط', subtitle: 'تجميع حسب الحالة', icon: 'solar:shield-warning-bold-duotone', color: '#c0392b' } as any));

const loading = ref(false);
const error = ref('');
const status = ref('');
const q = ref('');
const counts = ref<any>({open:0, under_review:0, closed:0});
const columns = ref<any>({open:[], under_review:[], closed:[]});
let timer:any = null;

async function reload(){
  loading.value = true; error.value='';
  try{
    const params:any = { limit: 20 };
    if (status.value) params.status = status.value;
    if (q.value) params.search = q.value;
    const data = await getKanban(params);
    counts.value = data?.counts || {open:0, under_review:0, closed:0};
    columns.value = data?.columns || {open:[], under_review:[], closed:[]};
  }catch(e:any){ error.value = e?.message || 'تعذّر التحميل'; }
  finally{ loading.value = false; }
}
function onSearchInput(){ clearTimeout(timer); timer = setTimeout(reload, 300); }

reload();
</script>
<style scoped>
.page-stack{ display:grid; gap:16px; }
.kanban-col{ border:1px solid #eee; border-radius:6px; background:#fff; }
.kanban-head{ padding:8px 12px; border-bottom:1px solid rgba(0,0,0,.05); border-top-left-radius:6px; border-top-right-radius:6px; font-weight:600; }
.kanban-body{ padding:8px; display:grid; gap:8px; max-height:70vh; overflow:auto; }
</style>
