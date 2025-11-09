<template>
  <section class="container py-3" dir="rtl">
    <div class="page-stack">
      <WingPageHeader class="mb-0" :icon="tileMeta.icon" :title="tileMeta.title" :color="tileMeta.color" :subtitle="tileMeta.subtitle">
        <template #actions>
          <input v-model.trim="q" @input="onSearchInput" type="search" class="form-control" placeholder="بحث بالكود/العنوان" style="max-width: 280px" />
        </template>
      </WingPageHeader>

      <div class="card p-0">
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
import { ref, computed } from 'vue';
import WingPageHeader from '../../../components/ui/WingPageHeader.vue';
import { tiles } from '../../../home/icon-tiles.config';
import { listViolations } from '../api';

const tileMeta = computed(()=> tiles.find(t=> t.to === '/discipline/violations') || ({ title: 'مخالفات السلوك', subtitle: 'كتالوج المستويات والإجراءات', icon: 'solar:shield-warning-bold-duotone', color: '#c0392b' } as any));

const items = ref<any[]>([]);
const loading = ref(false);
const q = ref('');
let timer:any = null;

async function load(){
  loading.value = true; items.value = [];
  try{
    const params:any = {};
    if (q.value) params.search = q.value;
    const data = await listViolations(params);
    // DRF paginated or list
    items.value = data?.results ?? data ?? [];
  } finally {
    loading.value = false;
  }
}

function onSearchInput(){ clearTimeout(timer); timer = setTimeout(load, 300); }

load();
</script>
<style scoped>
.page-stack{ display:grid; gap:16px; }
</style>
