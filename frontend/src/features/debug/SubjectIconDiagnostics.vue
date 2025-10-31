<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <div class="d-flex align-items-center gap-2 mb-2 header-bar frame">
      <Icon icon="solar:bookmark-square-bold-duotone" class="header-icon" />
      <div>
        <div class="fw-bold">تشخيص أيقونات المواد</div>
        <div class="text-muted small">قائمة المواد التي لا تملك أيقونات معبّرة (تقع على fallback)</div>
      </div>
      <span class="ms-auto"></span>
      <button class="btn btn-outline-secondary btn-sm" @click="refresh">تحديث</button>
    </div>

    <div class="auto-card p-3">
      <p class="m-0 small text-muted">
        لاستخراج قائمة دقيقة:
      </p>
      <ol class="small text-muted mb-2">
        <li>فعّل المتغير VITE_DEBUG_SUBJECT_ICONS=true داخل frontend/.env ثم شغّل الواجهة.</li>
        <li>تصفّح الصفحات التي تعرض المواد (جدول المعلم/الجناح اليومي والأسبوعي، السجل...)</li>
        <li>ارجع لهذه الصفحة لعرض وتجميع المواد التي سقطت على الأيقونة الافتراضية.</li>
      </ol>
      <div class="d-flex gap-2 flex-wrap mb-2">
        <button class="btn btn-sm btn-outline-primary" @click="copyRaw" :disabled="!raw.length">نسخ القائمة الأصلية</button>
        <button class="btn btn-sm btn-outline-primary" @click="copyNormalized" :disabled="!normalized.length">نسخ القائمة بعد التطبيع</button>
        <button class="btn btn-sm btn-outline-danger" @click="clearAll" :disabled="!raw.length && !normalized.length">مسح القائمة</button>
      </div>
      <div class="row g-3">
        <div class="col-12 col-md-6">
          <div class="card h-100">
            <div class="card-body">
              <h6 class="card-title">النصوص الأصلية (Raw)</h6>
              <div v-if="!raw.length" class="text-muted small">لا توجد بيانات بعد. تأكد من تفعيل العلم وزيارة صفحات الجداول.</div>
              <ul class="small m-0" v-else>
                <li v-for="s in raw" :key="'r-' + s">{{ s }}</li>
              </ul>
            </div>
          </div>
        </div>
        <div class="col-12 col-md-6">
          <div class="card h-100">
            <div class="card-body">
              <h6 class="card-title">النصوص بعد التطبيع (Normalized)</h6>
              <div v-if="!normalized.length" class="text-muted small">لا توجد بيانات بعد.</div>
              <ul class="small m-0" v-else>
                <li v-for="s in normalized" :key="'n-' + s">{{ s }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Icon } from "@iconify/vue";
import { ref, onMounted, watch } from "vue";
import { getSubjectIconDiagnostics, clearSubjectIconDiagnostics, enableSubjectIconDiagnosticsRuntime } from "../../shared/icons/subjectIcons";

const raw = ref<string[]>([]);
const normalized = ref<string[]>([]);
const debugEnabled = ref<boolean>(false);

function refresh() {
  const d = getSubjectIconDiagnostics();
  raw.value = d.raw;
  normalized.value = d.normalized;
}

function clearAll() {
  try { clearSubjectIconDiagnostics(); } catch {}
  refresh();
}

function toggleDebug() {
  debugEnabled.value = !debugEnabled.value;
  try { enableSubjectIconDiagnosticsRuntime(debugEnabled.value); } catch {}
}

function copy(text: string) {
  try {
    navigator.clipboard.writeText(text);
  } catch {}
}

function copyRaw() {
  copy(raw.value.join("\n"));
}
function copyNormalized() {
  copy(normalized.value.join("\n"));
}

onMounted(() => {
  // Enable diagnostics at runtime automatically to avoid depending on .env in dev
  debugEnabled.value = true;
  try { enableSubjectIconDiagnosticsRuntime(true); } catch {}
  refresh();
});
</script>

<style scoped>
.header-icon { font-size: 22px; }
</style>