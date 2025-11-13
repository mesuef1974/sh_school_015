<template>
  <div class="identity-stage">
    <div class="identity-stage-bg" aria-hidden="true"></div>
    <div class="container py-3">
      <div class="row justify-content-center">
        <div class="col-12 col-lg-8">
          <div class="card p-3 mb-3">
            <div class="d-flex align-items-center mb-3">
              <h2 class="h5 mb-0">ملفي الشخصي</h2>
              <span class="ms-auto"></span>
              <button class="btn btn-sm btn-outline-danger" @click.prevent="onLogout">
                <i class="bi bi-box-arrow-right"></i>
                تسجيل الخروج
              </button>
            </div>
            <div v-if="auth.loading">جاري التحميل…</div>
            <div v-else>
              <div class="row g-3">
                <div class="col-12 col-md-6">
                  <div class="form-floating">
                    <input
                      type="text"
                      class="form-control"
                      :value="auth.profile?.username"
                      readonly
                      id="fldUsername"
                    />
                    <label for="fldUsername">اسم المستخدم</label>
                  </div>
                </div>
                <div class="col-12 col-md-6">
                  <div class="form-floating">
                    <input
                      type="text"
                      class="form-control"
                      :value="auth.profile?.full_name"
                      readonly
                      id="fldFullname"
                    />
                    <label for="fldFullname">الاسم الكامل</label>
                  </div>
                </div>
                <div class="col-12">
                  <label class="form-label">الأدوار</label>
                  <div>
                    <span
                      v-for="r in auth.profile?.roles || []"
                      :key="r"
                      class="badge text-bg-secondary me-1"
                      >{{ r }}</span
                    >
                    <span v-if="(auth.profile?.roles || []).length === 0" class="text-muted"
                      >لا توجد أدوار محددة</span
                    >
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="card p-3">
            <h2 class="h6 mb-3">صلاحياتي ومهامي</h2>
            <div v-if="auth.profile" class="mb-3">
              <label class="form-label">القدرات الممنوحة</label>
              <div class="d-flex flex-wrap gap-2">
                <span
                  v-for="(val, key) in (auth.profile.capabilities || {})"
                  v-if="val"
                  :key="String(key)"
                  class="badge rounded-pill text-bg-primary"
                >{{ labelForCap(String(key)) }}</span>
                <span v-if="!anyCapability" class="text-muted">لا توجد قدرات خاصة</span>
              </div>
            </div>

            <div class="mb-2"><strong>ابدأ من هنا</strong></div>
            <div class="d-flex flex-wrap gap-2">
              <RouterLink v-if="can('can_take_attendance')" to="/attendance/teacher" class="btn btn-outline-primary btn-sm">
                تسجيل الغياب
              </RouterLink>
              <RouterLink v-if="can('discipline_l1') || can('discipline_l2')" to="/discipline/incidents/simple" class="btn btn-outline-secondary btn-sm">
                وقائع الانضباط
              </RouterLink>
              <RouterLink v-if="can('discipline_l2')" to="/discipline/violations" class="btn btn-outline-secondary btn-sm">
                كتالوج المخالفات
              </RouterLink>
              <RouterLink v-if="hasRole('wing_supervisor')" to="/wing/dashboard" class="btn btn-outline-success btn-sm">
                لوحة الجناح
              </RouterLink>
              <RouterLink v-if="hasRole('wing_supervisor')" to="/attendance/wing/monitor" class="btn btn-outline-success btn-sm">
                مراقبة حضور الجناح
              </RouterLink>
              <RouterLink v-if="can('can_approve_irreversible') || can('can_propose_irreversible')" to="/wing/approvals" class="btn btn-outline-warning btn-sm">
                طلبات الموافقة
              </RouterLink>
            </div>
          </div>

          <div class="card p-3 mt-3">
            <h2 class="h6 mb-3">تغيير كلمة المرور</h2>
            <form @submit.prevent="onChangePassword" class="row g-3">
              <div class="col-12 col-md-6">
                <label class="form-label">كلمة المرور الحالية</label>
                <input
                  v-model="current"
                  type="password"
                  class="form-control"
                  required
                  autocomplete="current-password"
                />
              </div>
              <div class="col-12 col-md-6"></div>
              <div class="col-12 col-md-6">
                <label class="form-label">كلمة المرور الجديدة</label>
                <input
                  v-model="new1"
                  type="password"
                  class="form-control"
                  required
                  autocomplete="new-password"
                />
              </div>
              <div class="col-12 col-md-6">
                <label class="form-label">تأكيد كلمة المرور الجديدة</label>
                <input
                  v-model="new2"
                  type="password"
                  class="form-control"
                  required
                  autocomplete="new-password"
                />
              </div>
              <div class="col-12 d-flex align-items-center gap-2">
                <button class="btn btn-maron" :disabled="saving">حفظ</button>
                <span v-if="msg" :class="{ 'text-success': success, 'text-danger': !success }">{{
                  msg
                }}</span>
              </div>
              <ul v-if="errors.length" class="text-danger small mb-0">
                <li v-for="(e, i) in errors" :key="i">{{ e }}</li>
              </ul>
            </form>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useAuthStore } from "../stores/auth";
import { changePassword, logout } from "../../shared/api/client";
import { useRouter } from "vue-router";

const auth = useAuthStore();
const router = useRouter();
const current = ref("");
const new1 = ref("");
const new2 = ref("");
const saving = ref(false);
const msg = ref("");
const success = ref(false);
const errors = ref<string[]>([]);

onMounted(async () => {
  if (!auth.profile && !auth.loading) {
    try {
      await auth.loadProfile();
    } catch {
      /* ignore */
    }
  }
});

const anyCapability = computed(() => {
  const caps = (auth.profile?.capabilities ?? {}) as Record<string, any>;
  return Object.keys(caps).some((k) => !!(caps as any)[k]);
});

function labelForCap(key: string) {
  const map: Record<string, string> = {
    can_manage_timetable: "إدارة الجداول",
    can_view_general_timetable: "عرض الجداول العامة",
    can_take_attendance: "تسجيل الحضور/الغياب",
    discipline_l1: "انضباط L1 (فرز أولي)",
    discipline_l2: "انضباط L2 (مراجعة/إجراءات)",
    exams_manage: "إدارة الاختبارات",
    health_can_view_masked: "عرض صحي مقنّع",
    health_can_unmask: "فك إخفاء صحي (ممرض)",
    can_propose_irreversible: "طلب إجراء غير قابل للعكس",
    can_approve_irreversible: "اعتماد إجراء غير قابل للعكس",
  };
  return map[key] || key;
}

function can(key: keyof NonNullable<ReturnType<typeof useAuthStore>["capabilities"]>) {
  return auth.can(key as any);
}

function hasRole(role: string) {
  return auth.hasRole(role);
}

async function onChangePassword() {
  saving.value = true;
  msg.value = "";
  success.value = false;
  errors.value = [];
  try {
    const res = await changePassword({
      current_password: current.value,
      new_password1: new1.value,
      new_password2: new2.value,
    });
    msg.value = res.detail || "تم تغيير كلمة المرور بنجاح";
    success.value = true;
    current.value = new1.value = new2.value = "";
  } catch (e: any) {
    const d = e?.response?.data;
    if (d?.errors && Array.isArray(d.errors)) {
      errors.value = d.errors;
      msg.value = "";
    } else {
      msg.value = d?.detail || "تعذر تغيير كلمة المرور";
    }
    success.value = false;
  } finally {
    saving.value = false;
  }
}

async function onLogout() {
  try {
    await logout();
  } finally {
    auth.clear();
    router.replace({ name: "login" });
  }
}
</script>

<style scoped>
.identity-stage {
  position: relative;
}
.identity-stage-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  /* solid maroon base with golden arabesque overlay */
  background-color: var(--maron-primary);
  background-image: url("/assets/img/arabesque_gs.svg");
  background-repeat: no-repeat;
  background-position: center;
  background-size: min(65%, 520px);
  background-attachment: fixed; /* pinned to viewport */
}
/* keep page content above the fixed background */
.identity-stage > .container {
  position: relative;
  z-index: 1;
}

.card {
  border-radius: 0.75rem;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.06);
}
</style>
