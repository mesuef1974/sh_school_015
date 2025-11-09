<template>
  <div class="mini" @click="$router.push({ name: 'discipline-incident-card', params: { id: it.id } })" role="button">
    <div class="d-flex justify-content-between align-items-center">
      <div class="fw-bold">{{ it.violation_display || it.violation_code || ('#'+it.violation) }}</div>
      <span class="badge" :style="{backgroundColor: it.level_color || '#2e7d32', color:'#fff'}">{{ it.severity ?? '—' }}</span>
    </div>
    <div class="small text-muted mt-1">{{ it.student_name || ('#'+it.student) }} • {{ fmtDate(it.occurred_at) }}</div>
    <div class="small mt-1" :title="it.narrative || ''">{{ truncate(it.narrative, 80) }}</div>
    <div class="d-flex gap-1 mt-2 align-items-center">
      <span class="badge" :class="badgeFor(it.status)">{{ statusAr(it.status) }}</span>
      <span class="badge bg-outline-primary text-primary">إج {{ it.actions_count ?? 0 }}</span>
      <span class="badge bg-outline-warning text-warning">عق {{ it.sanctions_count ?? 0 }}</span>
      <span v-if="it.committee_required" class="badge bg-danger">لجنة</span>
      <span v-if="it.is_overdue_review || it.is_overdue_notify" class="badge bg-danger">متجاوز SLA</span>
    </div>
  </div>
</template>
<script setup lang="ts">
const props = defineProps<{ it: any }>();

function fmtDate(s?: string){ if(!s) return '—'; try{ const d=new Date(s as string); const y=d.getFullYear(); const m=String(d.getMonth()+1).padStart(2,'0'); const dd=String(d.getDate()).padStart(2,'0'); return `${y}-${m}-${dd}`; }catch{ return s as string; } }
function truncate(s?: string, n=80){ if(!s) return '—'; return s.length>n? s.slice(0,n-1)+'…': s }
function badgeFor(st?: string){ return st==='closed'?'bg-secondary':(st==='under_review'?'bg-warning text-dark':'bg-info'); }
function statusAr(st?: string){ if(!st) return '—'; return st==='closed'?'مغلقة':(st==='under_review'?'قيد المراجعة':'مسودة'); }
</script>
<style scoped>
.mini{ border:1px solid #eee; border-radius:6px; padding:10px; background:#fff; cursor:pointer; }
.mini:hover{ box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.badge.bg-outline-primary{ border:1px solid #0d6efd; background:transparent; }
.badge.bg-outline-warning{ border:1px solid #f59f00; background:transparent; }
</style>