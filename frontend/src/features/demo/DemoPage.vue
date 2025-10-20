<template>
  <div class="demo-page">
    <Toaster position="top-center" richColors />

    <div class="auto-card p-4 mb-3">
      <h2 class="mb-3">اختبار المكتبات الجديدة</h2>

      <!-- PrimeVue Components -->
      <section class="mb-4">
        <h3 class="mb-2">PrimeVue</h3>
        <div class="d-flex gap-2 flex-wrap">
          <Button label="زر عادي" />
          <Button label="نجاح" severity="success" icon="pi pi-check" />
          <Button label="خطر" severity="danger" icon="pi pi-times" />
          <Button label="تحذير" severity="warning" icon="pi pi-exclamation-triangle" />
          <Button label="معلومات" severity="info" icon="pi pi-info-circle" />
        </div>
      </section>

      <!-- Vue Sonner Toasts -->
      <section class="mb-4">
        <h3 class="mb-2">Vue Sonner (إشعارات)</h3>
        <div class="d-flex gap-2 flex-wrap">
          <button class="btn btn-success" @click="showSuccess">نجاح</button>
          <button class="btn btn-danger" @click="showError">خطأ</button>
          <button class="btn btn-warning" @click="showWarning">تحذير</button>
          <button class="btn btn-info" @click="showInfo">معلومات</button>
        </div>
      </section>

      <!-- VueUse Motion -->
      <section class="mb-4">
        <h3 class="mb-2">VueUse Motion (حركات)</h3>
        <div class="d-flex gap-3 flex-wrap">
          <div
            v-motion
            :initial="{ opacity: 0, y: 100 }"
            :enter="{ opacity: 1, y: 0, transition: { delay: 100 } }"
            class="auto-card p-3"
            style="min-width: 150px"
          >
            <Icon icon="mdi:animation" class="fs-1 text-primary" />
            <p class="mb-0 mt-2">حركة من الأسفل</p>
          </div>

          <div
            v-motion
            :initial="{ opacity: 0, x: -100 }"
            :enter="{ opacity: 1, x: 0, transition: { delay: 200 } }"
            class="auto-card p-3"
            style="min-width: 150px"
          >
            <Icon icon="mdi:heart" class="fs-1 text-danger" />
            <p class="mb-0 mt-2">حركة من اليسار</p>
          </div>

          <div
            v-motion
            :initial="{ opacity: 0, scale: 0 }"
            :enter="{ opacity: 1, scale: 1, transition: { delay: 300 } }"
            class="auto-card p-3"
            style="min-width: 150px"
          >
            <Icon icon="mdi:star" class="fs-1 text-warning" />
            <p class="mb-0 mt-2">حركة تكبير</p>
          </div>
        </div>
      </section>

      <!-- PrimeVue DataTable Preview -->
      <section class="mb-4">
        <h3 class="mb-2">PrimeVue DataTable (جدول بيانات)</h3>
        <DataTable :value="students" stripedRows paginator :rows="5" tableStyle="min-width: 50rem">
          <Column field="id" header="الرقم" sortable></Column>
          <Column field="name" header="الاسم" sortable></Column>
          <Column field="grade" header="الصف" sortable></Column>
          <Column field="section" header="الشعبة" sortable></Column>
          <Column field="status" header="الحالة">
            <template #body="slotProps">
              <Tag
                :value="slotProps.data.status"
                :severity="slotProps.data.status === 'حاضر' ? 'success' : 'danger'"
              />
            </template>
          </Column>
        </DataTable>
      </section>

      <!-- VeeValidate Form -->
      <section class="mb-4">
        <h3 class="mb-2">VeeValidate (نموذج)</h3>
        <Form @submit="onSubmit" v-slot="{ errors }">
          <div class="mb-3">
            <label class="form-label">الاسم</label>
            <Field
              name="name"
              rules="required|min:3"
              v-slot="{ field, errors }"
            >
              <input v-bind="field" type="text" class="form-control" :class="{ 'is-invalid': errors.length }" />
              <div class="invalid-feedback">{{ errors[0] }}</div>
            </Field>
          </div>

          <div class="mb-3">
            <label class="form-label">البريد الإلكتروني</label>
            <Field
              name="email"
              rules="required|email"
              v-slot="{ field, errors }"
            >
              <input v-bind="field" type="email" class="form-control" :class="{ 'is-invalid': errors.length }" />
              <div class="invalid-feedback">{{ errors[0] }}</div>
            </Field>
          </div>

          <Button type="submit" label="إرسال" icon="pi pi-check" />
        </Form>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { toast } from 'vue-sonner';
import Button from 'primevue/button';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Tag from 'primevue/tag';
import { Form, Field, defineRule, configure } from 'vee-validate';
import { required, email, min } from '@vee-validate/rules';

// Configure VeeValidate rules
defineRule('required', required);
defineRule('email', email);
defineRule('min', min);

configure({
  generateMessage: (context) => {
    const messages: Record<string, string> = {
      required: 'هذا الحقل مطلوب',
      email: 'يجب إدخال بريد إلكتروني صحيح',
      min: `يجب أن يكون الحد الأدنى ${context.rule?.params?.[0]} أحرف`
    };
    return messages[context.rule?.name as string] || 'حقل غير صحيح';
  }
});

// Toast notifications
const showSuccess = () => toast.success('تمت العملية بنجاح!');
const showError = () => toast.error('حدث خطأ ما!');
const showWarning = () => toast.warning('تحذير: انتبه من فضلك');
const showInfo = () => toast.info('معلومة: هذا إشعار معلوماتي');

// Sample data for DataTable
const students = ref([
  { id: 1, name: 'أحمد محمد', grade: 'العاشر', section: 'أ', status: 'حاضر' },
  { id: 2, name: 'فاطمة علي', grade: 'التاسع', section: 'ب', status: 'غائب' },
  { id: 3, name: 'محمد خالد', grade: 'الحادي عشر', section: 'أ', status: 'حاضر' },
  { id: 4, name: 'سارة أحمد', grade: 'العاشر', section: 'ج', status: 'حاضر' },
  { id: 5, name: 'عمر حسن', grade: 'الثاني عشر', section: 'ب', status: 'غائب' },
  { id: 6, name: 'ليلى يوسف', grade: 'التاسع', section: 'أ', status: 'حاضر' },
  { id: 7, name: 'كريم صالح', grade: 'العاشر', section: 'ب', status: 'حاضر' },
  { id: 8, name: 'نور الدين', grade: 'الحادي عشر', section: 'ج', status: 'غائب' },
]);

// Form submit handler
const onSubmit = (values: any) => {
  toast.success(`تم إرسال النموذج: ${values.name}`);
  console.log('Form values:', values);
};
</script>

<style scoped>
.demo-page {
  max-width: 1200px;
  margin: 0 auto;
}

h2, h3 {
  color: var(--maron-primary);
}
</style>
