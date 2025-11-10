<template>
  <section class="container py-3" dir="rtl">
    <div class="page-stack">
      <WingPageHeader class="mb-0" :icon="tileMeta.icon" :title="tileMeta.title" :color="tileMeta.color" :subtitle="tileMeta.subtitle">
        <template #actions>
          <div class="d-flex gap-2 align-items-center">
            <select class="form-select" style="width: 160px" v-model="level" @change="onFilterChange">
              <option value="">كل المستويات</option>
              <option v-for="lvl in levels" :key="lvl.id" :value="lvl.code">المستوى {{ lvl.code }}</option>
            </select>
            <select class="form-select" style="width: 160px" v-model="severity" @change="onFilterChange">
              <option value="">كل الدرجات</option>
              <option v-for="s in severities" :key="s" :value="s">شدة {{ s }}</option>
            </select>
            <input v-model.trim="q" @input="onSearchInput" type="search" class="form-control" placeholder="بحث بالكود/العنوان" style="max-width: 280px" />
          </div>
        </template>
      </WingPageHeader>

      <div class="card p-0">
        <div class="px-3 pt-3 text-muted" v-if="!loading">
          <small>النتائج: {{ items.length }} عنصر</small>
        </div>
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th style="width: 80px">الكود</th>
                <th>التصنيف</th>
                <th style="width: 100px">المستوى</th>
                <th>وصف</th>
                <th style="width: 260px">إجراءات افتراضية</th>
                <th style="width: 260px">عقوبات افتراضية</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!loading && items.length===0">
                <td :colspan="6" class="text-center text-muted py-4">لا توجد نتائج مطابقة</td>
              </tr>
              <tr v-for="v in items" :key="v.id">
                <td><code>{{ v.code }}</code></td>
                <td><strong>{{ v.category }}</strong></td>
                <td><span class="badge bg-secondary">{{ v.severity }}</span></td>
                <td>{{ v.description }}</td>
                <td>
                  <ul class="m-0 ps-3">
                    <li v-for="a in v.default_actions" :key="a">{{ a }}</li>
                  </ul>
                </td>
                <td>
                  <ul class="m-0 ps-3">
                    <li v-for="s in v.default_sanctions" :key="s">{{ s }}</li>
                  </ul>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="loading" class="p-3 text-muted">جاري التحميل ...</div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import WingPageHeader from '../../../components/ui/WingPageHeader.vue';
import { tiles } from '../../../home/icon-tiles.config';
import { listViolations, listBehaviorLevels } from '../api';

const tileMeta = computed(()=> tiles.find(t=> t.to === '/discipline/violations') || ({ title: 'مخالفات السلوك', subtitle: 'كتالوج المستويات والإجراءات', icon: 'solar:shield-warning-bold-duotone', color: '#c0392b' } as any));

const items = ref<any[]>([]);
const levels = ref<any[]>([]);
const severities = [1,2,3,4,5];
const loading = ref(false);
const q = ref('');
const level = ref<string | number>('');
const severity = ref<string | number>('');
let timer:any = null;

async function load(){
  loading.value = true; items.value = [];
  try{
    const params:any = {};
    if (q.value) params.search = q.value;
    if (level.value !== '') params.level = level.value;
    if (severity.value !== '') params.severity = severity.value;
    const data = await listViolations(params);
    // DRF paginated or list
    items.value = data?.results ?? data ?? [];
  } finally {
    loading.value = false;
  }
}

function onSearchInput(){ clearTimeout(timer); timer = setTimeout(load, 300); }
function onFilterChange(){ load(); }

onMounted(async ()=>{
  try{
    const lvls = await listBehaviorLevels();
    levels.value = (lvls?.results ?? lvls ?? []).map((x:any)=> ({ id: x.id, code: x.code, name: x.name }));
  } catch {}
  load();
});
</script>
<style scoped>
.page-stack{ display:grid; gap:16px; }
</style>
