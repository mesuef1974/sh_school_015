<template>
  <section class="d-grid gap-3 page-grid page-grid-wide" dir="rtl">
    <!-- Header -->
    <div class="d-flex align-items-center gap-2 mb-2 header-bar frame">
      <Icon :icon="tileMeta.icon" class="header-icon" width="28" height="28" :style="{ color: tileMeta.color }" />
      <div>
        <div class="fw-bold">{{ tileMeta.title }}</div>
        <div class="text-muted small" v-if="wingLabelFull">{{ wingLabelFull }}</div>
        <div class="text-muted small" v-else>صفوف وطلبة جناحك — ابحث عن طالب مباشرةً</div>
      </div>
      <span class="ms-auto"></span>
      <div class="input-group w-auto" role="search" aria-label="بحث عن طالب">
        <input
          v-model.trim="qStudents"
          @keyup.enter="reloadStudents"
          class="form-control form-control-sm"
          :placeholder="'ابحث بالاسم أو الرقم المدرسي على مستوى الجناح'"
        />
        <button class="btn btn-sm btn-outline-secondary" type="button" @click="reloadStudents" aria-label="بحث الطلبة">
          <Icon icon="solar:magnifer-bold-duotone" />
        </button>
      </div>
    </div>

    <!-- No wing assigned message -->
    <div v-if="!loadingCtx && !hasWingRole && !isSuper" class="alert alert-warning">
      لا تملك صلاحية مشرف جناح، أو لم يُسند لك جناح بعد. يرجى التواصل مع الإدارة.
    </div>

    <div class="row g-3">
      <!-- Card: Classes list -->
      <div class="col-12 col-lg-5">
        <div class="card h-100" :aria-busy="loadingClasses ? 'true' : 'false'">
          <div class="card-body">
            <div class="d-flex align-items-center gap-2 mb-2">
              <Icon icon="solar:buildings-3-bold-duotone" class="text-primary" width="22" height="22" />
              <h5 class="m-0">صفوف الجناح</h5>
              <span class="badge text-bg-secondary ms-auto" :aria-live="'polite'">{{ classes.length }}</span>
            </div>

            <div v-if="errorClasses" class="alert alert-danger d-flex align-items-center gap-2">
              <Icon icon="solar:danger-triangle-bold-duotone" />
              <span>{{ errorClasses }}</span>
              <button class="btn btn-sm btn-outline-light ms-auto" @click="reloadClasses">إعادة المحاولة</button>
            </div>

            <div v-if="loadingClasses" class="text-muted small">جاري تحميل الصفوف ...</div>
            <ul v-else class="list-group list-group-flush class-list" role="listbox" aria-label="قائمة الصفوف">
              <li
                v-for="c in classes"
                :key="c.id"
                class="list-group-item d-flex align-items-center gap-2 list-item-hover"
                :class="{ active: c.id === selectedClassId }"
                role="option"
                :aria-selected="c.id === selectedClassId ? 'true' : 'false'"
                tabindex="0"
                @click="selectClass(c.id)"
                @keydown.enter.prevent="selectClass(c.id)"
                @keydown.space.prevent="selectClass(c.id)"
              >
                <Icon icon="solar:bookmark-square-bold-duotone" class="text-info" />
                <div class="flex-fill">
                  <div class="fw-semibold">{{ c.name }}</div>
                  <div class="small text-muted">المرحلة: {{ c.grade ?? '-' }} | الشعبة: {{ c.section || '-' }}</div>
                </div>
                <span class="badge rounded-pill text-bg-light" :title="'عدد الطلبة'">{{ c.students_count ?? 0 }}</span>
              </li>
              <li v-if="!classes.length" class="list-group-item text-muted">لا توجد صفوف ضمن جناحك.</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Card: Students of selected class -->
      <div class="col-12 col-lg-7">
        <div class="card h-100" :aria-busy="loadingStudents ? 'true' : 'false'">
          <div class="card-body d-flex flex-column">
            <div class="d-flex align-items-center gap-2 mb-2">
              <Icon icon="solar:users-group-two-rounded-bold-duotone" class="text-success" width="22" height="22" />
              <h5 class="m-0">الطلبة</h5>
              <span class="badge text-bg-secondary ms-auto" :aria-live="'polite'">{{ students.length }}</span>
            </div>

            <!-- البحث في الأعلى يعمل على مستوى الجناح بالكامل؛ اختيار الصف للتنقّل البصري فقط ولا يقيّد النتائج. -->

            <div v-if="errorStudents" class="alert alert-danger d-flex align-items-center gap-2">
              <Icon icon="solar:danger-triangle-bold-duotone" />
              <span>{{ errorStudents }}</span>
              <button class="btn btn-sm btn-outline-light ms-auto" @click="reloadStudents">إعادة المحاولة</button>
            </div>

            <div v-if="loadingStudents" class="text-muted small">جاري تحميل الطلبة ...</div>

            <div v-else class="table-responsive flex-fill">
              <table class="table align-middle table-sm">
                <thead>
                  <tr>
                    <th scope="col">#</th>
                    <th scope="col">الرقم المدرسي</th>
                    <th scope="col">اسم الطالب</th>
                    <th scope="col">الصف</th>
                    <th scope="col">ولي الأمر</th>
                    <th scope="col">أرقام التواصل</th>
                    <th scope="col">حالة اليوم</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(s, idx) in students" :key="s.id">
                    <td class="text-muted">{{ idx + 1 }}</td>
                    <td><code>{{ s.sid }}</code></td>
                    <td>{{ s.full_name }}</td>
                    <td>{{ s.class_name || '-' }}</td>
                    <td>{{ s.parent_name || '-' }}</td>
                    <td>
                      <div class="small lh-sm">
                        <div v-if="s.parent_phone">ولي: <a :href="`tel:${s.parent_phone}`">{{ s.parent_phone }}</a></div>
                        <div v-if="s.extra_phone_no">إضافي: <a :href="`tel:${s.extra_phone_no}`">{{ s.extra_phone_no }}</a></div>
                        <div v-if="s.phone_no" class="text-muted">طالب: <a :href="`tel:${s.phone_no}`">{{ s.phone_no }}</a></div>
                        <div v-if="!s.parent_phone && !s.extra_phone_no && !s.phone_no" class="text-muted">-</div>
                      </div>
                    </td>
                    <td>
                      <span v-if="dailyById[s.id]" class="att-chip day-state" :class="dailyById[s.id].state">
                        {{ humanState(dailyById[s.id].state) }}
                      </span>
                      <div v-if="dailyById[s.id]" class="small text-muted">
                        <span v-if="dailyById[s.id].p1">ح1: {{ shortStatus(dailyById[s.id].p1) }}</span>
                        <span v-if="dailyById[s.id].p2" class="ms-2">ح2: {{ shortStatus(dailyById[s.id].p2) }}</span>
                      </div>
                      <span v-else class="text-muted small">—</span>
                    </td>
                  </tr>
                  <tr v-if="!students.length">
                    <td colspan="7" class="text-muted">لا يوجد طلبة مطابقة للبحث.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Icon } from "@iconify/vue";
import { computed, onMounted, ref, watch } from "vue";
import { tiles } from "../../../home/icon-tiles.config";
import { useWingContext } from "../../../shared/composables/useWingContext";
import { getWingClasses, getWingStudents, getWingDailyAbsences } from "../../../shared/api/client";

const tileMeta = computed(() =>
  tiles.find((t) => t.to === "/wing/classes") || { title: "صفوف وطلبة", icon: "solar:home-2-bold-duotone", color: "#34495e" }
);
const { wingLabelFull, hasWingRole, isSuper, ensureLoaded, loading: loadingCtx } = useWingContext();

// Classes state
const classes = ref<{ id: number; name?: string; grade?: number; section?: string; students_count?: number }[]>([]);
const qClasses = ref("");
const loadingClasses = ref(false);
const errorClasses = ref<string | null>(null);

// Students state
const selectedClassId = ref<number | null>(null);
const students = ref<{ id: number; sid?: string; full_name?: string; class_name?: string; parent_name?: string | null; parent_phone?: string | null; extra_phone_no?: string | null; phone_no?: string | null }[]>([]);
const qStudents = ref("");
const loadingStudents = ref(false);
const errorStudents = ref<string | null>(null);
// Daily absence map for today keyed by student_id
const dailyById = ref<Record<number, { state: "excused" | "unexcused" | "none"; p1?: string | null; p2?: string | null }>>({});

function todayIso(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}
function humanState(s: string) {
  if (s === "excused") return "بعذر";
  if (s === "unexcused") return "بدون عذر";
  return "غير محسوب";
}
function shortStatus(s: any) {
  if (!s) return "-";
  const v = String(s);
  if (v === "present") return "ح";
  if (v === "absent") return "غ";
  if (v === "late") return "ت";
  if (v === "excused") return "إ";
  return v;
}

async function reloadClasses() {
  loadingClasses.value = true;
  errorClasses.value = null;
  try {
    const res = await getWingClasses({ q: qClasses.value || undefined });
    classes.value = res.items || [];
    // Preserve selection if still present; otherwise keep it null (search works wing-wide)
    if (selectedClassId.value && !classes.value.some((c) => c.id === selectedClassId.value)) {
      selectedClassId.value = null;
    }
  } catch (e: any) {
    errorClasses.value = e?.message || "فشل تحميل الصفوف";
  } finally {
    loadingClasses.value = false;
  }
}

function selectClass(classId: number) {
  selectedClassId.value = classId;
  // Load students for the selected class immediately (when no search query)
  // If there is an active search query, results remain wing-wide by design
  reloadStudents();
}

async function reloadStudents() {
  loadingStudents.value = true;
  errorStudents.value = null;
  try {
    // If there is a search query, search wing-wide; otherwise, if a class is selected, fetch that class's students
    const params: { q?: string; class_id?: number } = {};
    if (qStudents.value && qStudents.value.length > 0) {
      params.q = qStudents.value;
    } else if (selectedClassId.value) {
      params.class_id = selectedClassId.value;
    }

    const res = await getWingStudents(params);
    students.value = res.items || [];
    // Fetch today's daily absences and map by student_id, scoping to class if applicable for performance
    try {
      const dailyParams: { date: string; class_id?: number } = { date: todayIso() };
      if (!params.q && params.class_id) dailyParams.class_id = params.class_id;
      const daily = await getWingDailyAbsences(dailyParams);
      const map: Record<number, any> = {};
      for (const it of daily.items || []) {
        map[it.student_id] = { state: it.state, p1: it.p1, p2: it.p2 };
      }
      dailyById.value = map as any;
    } catch (e) {
      dailyById.value = {} as any;
    }
  } catch (e: any) {
    errorStudents.value = e?.message || "فشل تحميل الطلبة";
  } finally {
    loadingStudents.value = false;
  }
}


onMounted(async () => {
  await ensureLoaded();
  await reloadClasses();
});
</script>

<style scoped>
.header-icon { font-size: 22px; }
.list-item-hover { cursor: pointer; }
.list-group-item.active {
  background-color: rgba(13, 110, 253, 0.1); /* fallback subtle primary */
}
.class-list { max-height: 60vh; overflow: auto; }
</style>