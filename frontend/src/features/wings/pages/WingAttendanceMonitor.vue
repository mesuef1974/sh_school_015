<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <!-- صفحة مراقبة حضور الجناح - رأس موحّد مع أيقونة الطباعة -->
    <WingPageHeader :icon="tileMeta.icon" :title="tileMeta.title" :color="tileMeta.color">
      <template #actions>
        <WingWingPicker id="pick-monitor-wing" />
      </template>
    </WingPageHeader>

    <!-- شريط أدوات التصفية -->
    <div class="auto-card p-2 d-flex align-items-center gap-2 flex-wrap" role="search" aria-label="مرشحات مراقبة الحضور">
      <div class="d-flex align-items-center gap-2 flex-wrap">
        <label class="form-label m-0 small">التاريخ</label>
        <input type="date" class="form-control form-control-sm" v-model="dateStr" style="width:auto" />
      </div>
      <div class="d-flex align-items-center gap-2 flex-wrap ms-3">
        <label class="form-label m-0 small">الوضع</label>
        <div class="btn-group btn-group-sm" role="group" aria-label="وضع العرض">
          <button type="button" class="btn" :class="mode==='daily'? 'btn-primary' : 'btn-outline-primary'" @click="mode='daily'">يومي</button>
          <button type="button" class="btn" :class="mode==='period'? 'btn-primary' : 'btn-outline-primary'" @click="mode='period'">حسب الحصص</button>
        </div>
      </div>
      <span class="ms-auto small text-muted" aria-live="polite">{{ subtitle }}</span>
    </div>

    <!-- بطاقات مؤشرات مختصرة -->
    <div class="row g-3">
      <div class="col-6 col-md-3">
        <div class="card h-100">
          <div class="card-body d-flex flex-column">
            <div class="text-muted small">إجمالي الصفوف</div>
            <div class="display-6" dir="ltr">{{ kpis.classes ?? '--' }}</div>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="card h-100">
          <div class="card-body d-flex flex-column">
            <div class="text-muted small">إجمالي الطلبة</div>
            <div class="display-6" dir="ltr">{{ kpis.students ?? '--' }}</div>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="card h-100">
          <div class="card-body d-flex flex-column">
            <div class="text-muted small">نسبة الحضور</div>
            <div class="display-6" dir="ltr">{{ kpis.attendance_rate ?? '--%' }}</div>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="card h-100">
          <div class="card-body d-flex flex-column">
            <div class="text-muted small">عدد التأخرات</div>
            <div class="display-6" dir="ltr">{{ kpis.lates ?? '--' }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- جدول تفصيلي للصفوف -->
    <div class="card">
      <div class="card-body">
        <div class="d-flex align-items-center gap-2 mb-2">
          <Icon icon="solar:radar-2-bold-duotone" class="text-primary" width="22" height="22" />
          <h5 class="m-0 card-title-maroon">تفصيل الصفوف</h5>
        </div>
        <div class="table-responsive">
          <table class="table table-sm align-middle print-table">
            <thead>
              <tr>
                <th>#</th>
                <th>الصف</th>
                <th>عدد الطلبة</th>
                <th>حاضر</th>
                <th>غائب بدون عذر</th>
                <th>غائب بعذر</th>
                <th>متأخر</th>
                <th>نسبة الحضور</th>
                <th>ملاحظات</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in rows" :key="row.id">
                <td class="text-muted">{{ i+1 }}</td>
                <td>{{ row.class_name }}</td>
                <td>{{ row.students_count ?? '-' }}</td>
                <td>{{ row.present ?? '-' }}</td>
                <td>{{ row.absent_unexcused ?? '-' }}</td>
                <td>{{ row.absent_excused ?? '-' }}</td>
                <td>{{ row.late ?? '-' }}</td>
                <td>{{ row.rate ?? '--%' }}</td>
                <td>{{ row.note || '-' }}</td>
              </tr>
              <tr v-if="!rows.length">
                <td colspan="9" class="text-muted">لا توجد بيانات بعد — الصفحة قيد التطوير.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</template>
<script setup lang="ts">
import { Icon } from "@iconify/vue";
import { computed, onMounted, ref, watch } from 'vue';
import { tiles } from "../../../home/icon-tiles.config";
import WingPageHeader from "../../../components/ui/WingPageHeader.vue";
import WingWingPicker from "../../../components/ui/WingWingPicker.vue";
import { useWingContext } from '../../../shared/composables/useWingContext';
import { useWingPrefs } from '../../../shared/composables/useWingPrefs';

const tileMeta = computed(() => tiles.find(t => t.to === "/attendance/wing/monitor") || { title: "مراقبة حضور الجناح", icon: "solar:radar-2-bold-duotone", color: "#0d47a1" });

const { ensureLoaded, wingLabelFull, selectedWingId } = useWingContext();
const { default_date_mode } = useWingPrefs();

function todayIso(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${dd}`;
}

const dateStr = ref<string>(todayIso());
const mode = ref<'daily'|'period'>('daily');

onMounted(async () => {
  await ensureLoaded();
  // تهيئة التاريخ حسب تفضيلات الجناح إن لزم
  const m = default_date_mode.value;
  if (m === 'today') dateStr.value = todayIso();
  // TODO: لاحقًا دعم remember/last عبر localStorage عند ربط البيانات
});

// بيانات مؤشرات وكشف — قيد التطوير: نضع بنية جاهزة للربط لاحقًا
const kpis = ref<{ classes?: number; students?: number; attendance_rate?: string; lates?: number }>({});
const rows = ref<Array<{ id:number; class_name:string; students_count?:number; present?:number; absent_unexcused?:number; absent_excused?:number; late?:number; rate?:string; note?:string }>>([]);

const subtitle = computed(() => wingLabelFull.value || '');

// نقاط ربط مستقبلية: عند تغيير التاريخ/الوضع/الجناح سيتم الطلب من API
watch([dateStr, mode, selectedWingId], () => {
  // TODO: استدعاء API لملء kpis و rows
});
</script>
<style scoped>
.table-card { margin-top: 0.5rem; }
</style>