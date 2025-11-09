<template>
  <section class="container py-3" dir="rtl">
    <div class="page-stack">
      <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" :color="tileMeta.color" :subtitle="tileMeta.subtitle" />

      <div class="card p-3">
        <div class="row g-3 align-items-end">
        <div class="col-md-3 col-12">
          <label class="form-label">الحالة</label>
          <select v-model="status" class="form-select" @change="reload">
            <option value="under_review">قيد المراجعة</option>
            <option value="open">مسودة</option>
            <option value="closed">مغلقة</option>
          </select>
        </div>
        <div class="col-md-6 col-12">
          <label class="form-label">بحث</label>
          <input v-model.trim="q" @input="onSearchInput" type="search" class="form-control" placeholder="بحث بالوصف/المكان/المخالفة" />
        </div>
      </div>
    </div>

    <div class="card p-0 mt-3">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>التاريخ</th>
              <th>المخالفة</th>
              <th>الطالب</th>
              <th>الشدة</th>
              <th>لجنة؟</th>
              <th>الحالة</th>
              <th style="width:260px">إجراءات</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!loading && items.length===0">
              <td :colspan="7" class="text-center text-muted py-4">لا توجد سجلات</td>
            </tr>
            <tr v-for="it in items" :key="it.id">
              <td>{{ fmtDate(it.occurred_at) }}</td>
              <td><strong>{{ it.violation_display || it.violation?.code }}</strong></td>
              <td>#{{ it.student }}</td>
              <td><span class="badge bg-secondary">{{ it.severity }}</span></td>
              <td>
                <span class="badge" :class="it.committee_required ? 'bg-danger' : 'bg-success'">{{ it.committee_required? 'نعم':'لا' }}</span>
              </td>
              <td>
                <span class="badge" :class="badgeFor(it.status)">{{ statusAr(it.status) }}</span>
              </td>
              <td class="d-flex gap-2">
                <button class="btn btn-sm btn-outline-primary" :disabled="busyId===it.id" @click="markReviewed(it.id)">تسجيل مراجعة</button>
                <button class="btn btn-sm btn-outline-success" :disabled="busyId===it.id" @click="addAction(it.id)">إضافة إجراء</button>
                <button class="btn btn-sm btn-outline-warning" :disabled="busyId===it.id" @click="addSanction(it.id)">إضافة عقوبة</button>
                <button class="btn btn-sm btn-outline-secondary" :disabled="busyId===it.id" @click="closeIncident(it.id)">إغلاق</button>
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
import { ref } from 'vue';
import { api } from '../../../shared/api/client';
import { listIncidents } from '../api';

const items = ref<any[]>([]);
const loading = ref(false);
const status = ref('under_review');
const q = ref('');
const busyId = ref<string| null>(null);
let timer:any = null;

async function reload(){
  loading.value = true; items.value = [];
  try{
    const params:any = {};
    if (q.value) params.search = q.value;
    const data = await listIncidents(params);
    items.value = (data?.results ?? data ?? []).filter((x:any)=> !status.value || x.status===status.value);
  } finally {
    loading.value = false;
  }
}

function onSearchInput(){ clearTimeout(timer); timer = setTimeout(reload, 300); }

async function markReviewed(id: string){ await post(id, 'review'); }
async function addAction(id: string){ const name = window.prompt('اسم الإجراء:'); if(!name) return; await post(id, 'add-action', { name }); }
async function addSanction(id: string){ const name = window.prompt('اسم العقوبة:'); if(!name) return; await post(id, 'add-sanction', { name }); }
async function closeIncident(id: string){ await post(id, 'close'); }

async function post(id: string, action: string, payload?: any){
  try{
    busyId.value = id;
    await api.post(`/v1/discipline/incidents/${id}/${action}/`, payload||{});
    await reload();
  } finally {
    busyId.value = null;
  }
}

function fmtDate(s?: string){ if(!s) return '—'; try{ const d=new Date(s); const y=d.getFullYear(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${dd}`; }catch{ return s as string; } }
function badgeFor(st: string){ return st==='closed'?'bg-secondary':(st==='under_review'?'bg-warning text-dark':'bg-info'); }
function statusAr(st: string){ return st==='closed'?'مغلقة':(st==='under_review'?'قيد المراجعة':'مسودة'); }

reload();
</script>
