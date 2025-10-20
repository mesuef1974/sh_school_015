<template>
  <div class="design-system-showcase">
    <Toaster position="top-center" richColors />

    <!-- Hero Section -->
    <DsCard
      title="نظام التصميم - مدرسة الشحانية"
      :animate="true"
      class="hero-card mb-4"
    >
      <template #header>
        <div class="d-flex align-items-center gap-3">
          <Icon icon="mdi:palette" class="text-4xl" style="color: var(--maron-primary)" />
          <div>
            <h1 class="mb-1" style="color: var(--maron-primary)">نظام التصميم المتكامل</h1>
            <p class="text-muted mb-0">تطبيق أفضل المعايير العالمية في تصميم منصات الإدارة المدرسية</p>
          </div>
        </div>
      </template>

      <div class="row g-4">
        <div class="col-md-3 col-6">
          <div class="stat-box text-center p-3">
            <Icon icon="mdi:check-circle" class="text-4xl mb-2" style="color: var(--color-success)" />
            <div class="text-2xl font-bold">WCAG 2.1</div>
            <div class="text-sm text-muted">معايير الوصول</div>
          </div>
        </div>
        <div class="col-md-3 col-6">
          <div class="stat-box text-center p-3">
            <Icon icon="mdi:responsive" class="text-4xl mb-2" style="color: var(--color-info)" />
            <div class="text-2xl font-bold">Responsive</div>
            <div class="text-sm text-muted">متجاوب كلياً</div>
          </div>
        </div>
        <div class="col-md-3 col-6">
          <div class="stat-box text-center p-3">
            <Icon icon="mdi:speedometer" class="text-4xl mb-2" style="color: var(--color-warning)" />
            <div class="text-2xl font-bold">Fast</div>
            <div class="text-sm text-muted">أداء عالي</div>
          </div>
        </div>
        <div class="col-md-3 col-6">
          <div class="stat-box text-center p-3">
            <Icon icon="mdi:brush" class="text-4xl mb-2" style="color: var(--maron-accent)" />
            <div class="text-2xl font-bold">Modern</div>
            <div class="text-sm text-muted">تصميم عصري</div>
          </div>
        </div>
      </div>
    </DsCard>

    <!-- Colors Section -->
    <DsCard title="نظام الألوان" :delay="100" class="mb-4">
      <div class="row g-3">
        <div class="col-md-2 col-4">
          <div class="color-swatch" style="background: var(--maron-primary)">
            <span class="color-label">Primary</span>
          </div>
        </div>
        <div class="col-md-2 col-4">
          <div class="color-swatch" style="background: var(--maron-accent)">
            <span class="color-label">Accent</span>
          </div>
        </div>
        <div class="col-md-2 col-4">
          <div class="color-swatch" style="background: var(--color-success)">
            <span class="color-label">Success</span>
          </div>
        </div>
        <div class="col-md-2 col-4">
          <div class="color-swatch" style="background: var(--color-warning)">
            <span class="color-label">Warning</span>
          </div>
        </div>
        <div class="col-md-2 col-4">
          <div class="color-swatch" style="background: var(--color-danger)">
            <span class="color-label">Danger</span>
          </div>
        </div>
        <div class="col-md-2 col-4">
          <div class="color-swatch" style="background: var(--color-info)">
            <span class="color-label">Info</span>
          </div>
        </div>
      </div>
    </DsCard>

    <!-- Buttons Section -->
    <DsCard title="الأزرار (Buttons)" :delay="150" class="mb-4">
      <div class="d-flex flex-wrap gap-3 mb-4">
        <DsButton variant="primary" icon="mdi:check">زر أساسي</DsButton>
        <DsButton variant="success" icon="mdi:check-circle">نجاح</DsButton>
        <DsButton variant="danger" icon="mdi:alert-circle">خطر</DsButton>
        <DsButton variant="warning" icon="mdi:alert">تحذير</DsButton>
        <DsButton variant="info" icon="mdi:information">معلومات</DsButton>
      </div>

      <div class="d-flex flex-wrap gap-3 mb-4">
        <DsButton size="sm" variant="primary">صغير</DsButton>
        <DsButton size="md" variant="primary">متوسط</DsButton>
        <DsButton size="lg" variant="primary">كبير</DsButton>
      </div>

      <div class="d-flex flex-wrap gap-3">
        <DsButton :loading="true" variant="primary">جاري التحميل...</DsButton>
        <DsButton :disabled="true" variant="primary">معطّل</DsButton>
      </div>
    </DsCard>

    <!-- Badges Section -->
    <DsCard title="الشارات (Badges)" :delay="200" class="mb-4">
      <div class="d-flex flex-wrap gap-3 align-items-center">
        <DsBadge variant="success" icon="mdi:check-circle">حاضر</DsBadge>
        <DsBadge variant="danger" icon="mdi:close-circle">غائب</DsBadge>
        <DsBadge variant="warning" icon="mdi:clock-outline">متأخر</DsBadge>
        <DsBadge variant="info" icon="mdi:information">معلومة</DsBadge>
        <DsBadge variant="success" size="sm">صغير</DsBadge>
        <DsBadge variant="info" size="lg">كبير</DsBadge>
      </div>
    </DsCard>

    <!-- Notifications Section -->
    <DsCard title="الإشعارات (Notifications)" :delay="250" class="mb-4">
      <div class="d-flex flex-wrap gap-3">
        <DsButton @click="showSuccess" icon="mdi:check-circle">نجاح</DsButton>
        <DsButton @click="showError" icon="mdi:alert-circle">خطأ</DsButton>
        <DsButton @click="showWarning" icon="mdi:alert">تحذير</DsButton>
        <DsButton @click="showInfo" icon="mdi:information">معلومة</DsButton>
      </div>
    </DsCard>

    <!-- Alerts Section -->
    <DsCard title="التنبيهات (Alerts)" :delay="300" class="mb-4">
      <div class="d-grid gap-3">
        <div class="ds-alert ds-alert-success">
          <Icon icon="mdi:check-circle" class="text-xl" />
          <div>
            <strong>نجاح!</strong> تم حفظ البيانات بنجاح.
          </div>
        </div>
        <div class="ds-alert ds-alert-warning">
          <Icon icon="mdi:alert" class="text-xl" />
          <div>
            <strong>تحذير!</strong> يرجى مراجعة البيانات المدخلة.
          </div>
        </div>
        <div class="ds-alert ds-alert-danger">
          <Icon icon="mdi:alert-circle" class="text-xl" />
          <div>
            <strong>خطأ!</strong> حدث خطأ أثناء معالجة الطلب.
          </div>
        </div>
        <div class="ds-alert ds-alert-info">
          <Icon icon="mdi:information" class="text-xl" />
          <div>
            <strong>معلومة:</strong> يمكنك تحديث البيانات في أي وقت.
          </div>
        </div>
      </div>
    </DsCard>

    <!-- Typography Section -->
    <DsCard title="الطباعة (Typography)" :delay="350" class="mb-4">
      <div class="text-4xl font-bold mb-2">عنوان رئيسي (4XL)</div>
      <div class="text-3xl font-bold mb-2">عنوان ثانوي (3XL)</div>
      <div class="text-2xl font-semibold mb-2">عنوان فرعي (2XL)</div>
      <div class="text-xl font-medium mb-2">عنوان صغير (XL)</div>
      <div class="text-lg mb-2">نص كبير (LG)</div>
      <div class="text-base mb-2">نص عادي (Base)</div>
      <div class="text-sm mb-2">نص صغير (SM)</div>
      <div class="text-xs">نص صغير جداً (XS)</div>
    </DsCard>

    <!-- Data Table Preview -->
    <DsCard title="جدول بيانات (Data Table)" :delay="400" class="mb-4">
      <DataTable
        :value="students"
        stripedRows
        paginator
        :rows="5"
        :rowsPerPageOptions="[5, 10, 20]"
        tableStyle="min-width: 50rem"
      >
        <Column field="id" header="الرقم" sortable style="width: 80px"></Column>
        <Column field="name" header="الاسم" sortable></Column>
        <Column field="grade" header="الصف" sortable></Column>
        <Column field="section" header="الشعبة" sortable></Column>
        <Column field="status" header="الحالة">
          <template #body="slotProps">
            <DsBadge
              :variant="slotProps.data.status === 'حاضر' ? 'success' : 'danger'"
              :icon="slotProps.data.status === 'حاضر' ? 'mdi:check-circle' : 'mdi:close-circle'"
            >
              {{ slotProps.data.status }}
            </DsBadge>
          </template>
        </Column>
      </DataTable>
    </DsCard>

    <!-- Loading Skeleton -->
    <DsCard title="Loading Skeleton" :delay="450">
      <div class="d-grid gap-3">
        <div class="ds-skeleton" style="height: 40px"></div>
        <div class="ds-skeleton" style="height: 80px"></div>
        <div class="d-flex gap-3">
          <div class="ds-skeleton" style="height: 40px; flex: 1"></div>
          <div class="ds-skeleton" style="height: 40px; flex: 1"></div>
        </div>
      </div>
    </DsCard>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { toast } from 'vue-sonner';
import DsButton from '../../components/ui/DsButton.vue';
import DsCard from '../../components/ui/DsCard.vue';
import DsBadge from '../../components/ui/DsBadge.vue';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';

// Sample data
const students = ref([
  { id: 1, name: 'أحمد محمد علي', grade: 'العاشر', section: 'أ', status: 'حاضر' },
  { id: 2, name: 'فاطمة حسن', grade: 'التاسع', section: 'ب', status: 'غائب' },
  { id: 3, name: 'محمد خالد', grade: 'الحادي عشر', section: 'أ', status: 'حاضر' },
  { id: 4, name: 'سارة أحمد', grade: 'العاشر', section: 'ج', status: 'حاضر' },
  { id: 5, name: 'عمر حسن', grade: 'الثاني عشر', section: 'ب', status: 'غائب' },
  { id: 6, name: 'ليلى يوسف', grade: 'التاسع', section: 'أ', status: 'حاضر' },
  { id: 7, name: 'كريم صالح', grade: 'العاشر', section: 'ب', status: 'حاضر' },
  { id: 8, name: 'نور محمود', grade: 'الحادي عشر', section: 'ج', status: 'غائب' },
]);

// Toast notifications
const showSuccess = () => toast.success('تمت العملية بنجاح!', { description: 'تم حفظ البيانات بنجاح' });
const showError = () => toast.error('حدث خطأ!', { description: 'لم نتمكن من معالجة الطلب' });
const showWarning = () => toast.warning('تحذير!', { description: 'يرجى مراجعة البيانات المدخلة' });
const showInfo = () => toast.info('معلومة', { description: 'يمكنك تحديث البيانات في أي وقت' });
</script>

<style scoped>
.design-system-showcase {
  max-width: 1400px;
  margin: 0 auto;
  padding: var(--space-6);
}

.hero-card {
  background: linear-gradient(135deg, var(--maron-bg) 0%, #ffffff 100%);
}

.stat-box {
  background: white;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-base);
}

.stat-box:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
}

.color-swatch {
  height: 120px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: flex-end;
  padding: var(--space-3);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-base);
}

.color-swatch:hover {
  transform: scale(1.05);
  box-shadow: var(--shadow-md);
}

.color-label {
  color: white;
  font-weight: var(--font-weight-semibold);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}
</style>
