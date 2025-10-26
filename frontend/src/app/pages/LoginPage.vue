<template>
  <div class="login-container">
    <div class="login-stage">
      <div class="login-wrapper">
        <div class="login-wrapper-bg" aria-hidden="true"></div>
        <!-- Left Side - Branding -->
      <div
        class="login-brand"
      >
        <div class="brand-content">
          <span class="brand-logo-mask" aria-hidden="true"></span>
          <h1 class="brand-title text-gold-metal">مدرسة الشحانية</h1>
          <p class="brand-subtitle text-gold-metal">الإعدادية الثانوية للبنين</p>
          <div class="brand-divider"></div>
          <p class="brand-description text-gold-metal">
            منصة الإدارة المدرسية الذكية
            <br />
            إدارة شاملة وتقارير فورية
          </p>

          <!-- Features -->
          <div class="features-list">
            <div class="feature-item">
              <Icon icon="solar:check-circle-bold-duotone" class="feature-icon" />
              <span class="text-gold-metal">إدارة الحضور والغياب</span>
            </div>
            <div class="feature-item">
              <Icon icon="solar:check-circle-bold-duotone" class="feature-icon" />
              <span class="text-gold-metal">تقارير تفصيلية فورية</span>
            </div>
            <div class="feature-item">
              <Icon icon="solar:check-circle-bold-duotone" class="feature-icon" />
              <span class="text-gold-metal">واجهة سهلة الاستخدام</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Side - Login Form -->
      <div
        class="login-form-wrapper"
      >
        <DsCard
          class="login-card"
          :animate="false"
        >
          <div class="login-header">
            <Icon icon="solar:shield-check-bold-duotone" class="login-card-logo" aria-hidden="true" />
            <h2 class="login-title">تسجيل الدخول</h2>
            <p class="login-subtitle">أدخل بيانات الدخول للوصول إلى المنصة</p>
          </div>

          <form @submit.prevent="onSubmit" class="login-form">
            <!-- Username Field -->
            <div class="form-group">
              <label class="form-label">
                <Icon icon="solar:user-bold-duotone" class="label-icon" />
                اسم المستخدم
              </label>
              <input
                v-model="username"
                type="text"
                class="form-control ds-input"
                placeholder="أدخل اسم المستخدم"
                required
                autocomplete="username"
                :disabled="loading"
              />
            </div>

            <!-- Password Field -->
            <div class="form-group">
              <label class="form-label">
                <Icon icon="solar:lock-password-bold-duotone" class="label-icon" />
                كلمة المرور
              </label>
              <div class="password-input-wrapper">
                <input
                  v-model="password"
                  :type="showPassword ? 'text' : 'password'"
                  class="form-control ds-input"
                  placeholder="أدخل كلمة المرور"
                  required
                  autocomplete="current-password"
                  :disabled="loading"
                />
                <button
                  type="button"
                  class="password-toggle"
                  @click="showPassword = !showPassword"
                  :disabled="loading"
                >
                  <Icon :icon="showPassword ? 'solar:eye-closed-bold-duotone' : 'solar:eye-bold-duotone'" />
                </button>
              </div>
            </div>

            <!-- Error Alert -->
            <div v-if="error" class="ds-alert ds-alert-danger" role="alert">
              <Icon icon="solar:danger-circle-bold-duotone" class="text-xl" />
              <div>{{ error }}</div>
            </div>

            <!-- Submit Button -->
            <DsButton
              type="submit"
              variant="primary"
              size="lg"
              :loading="loading"
              :disabled="loading"
              icon="solar:shield-check-bold-duotone"
              class="w-100"
            >
              {{ loading ? 'جاري الدخول...' : 'دخول' }}
            </DsButton>
          </form>

          <!-- Footer -->
          <div class="login-footer">
            <p class="text-muted text-sm text-center mb-0">
              جميع الحقوق محفوظة © {{ currentYear }}
            </p>
          </div>
        </DsCard>
      </div>
    </div>
  </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { login } from '../../shared/api/client';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { toast } from 'vue-sonner';
import DsButton from '../../components/ui/DsButton.vue';
import DsCard from '../../components/ui/DsCard.vue';

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const username = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');
const showPassword = ref(false);
const logoSrc = '/assets/img/logo.png';
const currentYear = computed(() => new Date().getFullYear());

async function onSubmit() {
  loading.value = true;
  error.value = '';

  try {
    await login(username.value, password.value);

    try {
      await auth.loadProfile();
    } catch {
      // Ignore profile load errors
    }

    toast.success('مرحباً بك!', {
      description: 'تم تسجيل الدخول بنجاح'
    });

    const next = (route.query.next as string) || '';
    const primary = auth.profile?.primary_route || '';
    const roles = auth.profile?.roles || [];
    const isOnlyTeacher = roles.includes('teacher') && !roles.some(r => ['principal','academic_deputy','timetable_manager','subject_coordinator','wing_supervisor'].includes(r));

    if (next) {
      router.replace(next);
    } else if (isOnlyTeacher) {
      // توجيه المعلم فقط إلى الصفحة الرئيسية بدل صفحة الغياب مباشرةً
      router.replace('/');
    } else if (primary) {
      router.replace(primary);
    } else {
      // Fallback to home if no hint provided
      router.replace('/');
    }
  } catch (e: any) {
    if (!e?.response) {
      error.value = 'الخادم غير متاح الآن. تأكد من تشغيل الباك-إند ثم أعد المحاولة.';
    } else {
      error.value = e?.response?.data?.detail || 'بيانات الدخول غير صحيحة';
    }

    toast.error('فشل تسجيل الدخول', {
      description: error.value
    });
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-container {
  /* Fit exactly between header and footer to avoid any vertical scroll */
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  /* Make the page-level background transparent so arabesque appears only inside the golden frame */
  background: transparent;
  padding: 0;
  overflow: hidden; /* prevent scrollbars on the login page */
}

/* Stage wrapper (no outer border now; golden frame will be on the card itself) */
.login-stage {
  position: relative;
  display: block;
  width: 100%;
  max-width: 1280px;
  margin-inline: auto;
  border-radius: var(--radius-2xl);
  background: transparent;
  padding: 0;
}


.login-wrapper {
  /* Tuning knobs */
  --login-frame-w: 10px;        /* golden border width */

  max-width: 1200px;
  width: 100%;
  margin-inline: auto; /* ensure centered horizontally within container */
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-8);
  align-items: center;           /* prevent children from stretching vertically */
  justify-items: center;         /* keep both columns' contents centered horizontally */
  /* Backdrop card behind both the branding and the login panel */
  position: relative;
  border-radius: 0; /* square corners */
  border: var(--login-frame-w) solid transparent; /* show gold frame via gradient border */
  background:
    /* Ensure interior is solid maroon, only the border shows gold */
    linear-gradient(var(--maron-primary), var(--maron-primary)) padding-box,
    conic-gradient(from 0deg,
      #8B7500 0%,
      #B08D57 12%,
      #D4AF37 25%,
      #FFD700 37%,
      #B08D57 50%,
      #8B7500 62%,
      #E6C200 75%,
      #FFD700 87%,
      #B08D57 100%
    ) border-box;
  -webkit-backdrop-filter: none; /* remove blur */
  backdrop-filter: none;         /* remove blur */
  box-shadow: none;              /* remove shadow */
  padding: var(--space-8);
}




/* Animated glossy shine over the golden frame */


/* Inner maroon fill moved into a dedicated background element to avoid conflicts with ::after */
.login-wrapper-bg {
  position: absolute;
  inset: var(--login-frame-w);
  border-radius: inherit;
  pointer-events: none;
  z-index: 0;
  /* Solid maroon interior */
  background: var(--maron-primary);
  /* Keep the interior static and readable */
  filter: none;
  opacity: 1;
}


/* Animated glossy shine over the golden frame */

/* Inner maroon fill only (no shine) */

/* Ensure all children sit above the ::after cover */
.login-wrapper > * {
  position: relative;
  z-index: 1;
}

/* Disable interior animations inside the two panels only; allow entrance on the panels themselves
   Allow shine animation on the brand logo mask exclusively */
.login-form-wrapper * {
  animation: none !important;
}
.login-brand *:not(.brand-logo-mask) {
  animation: none !important;
}
/* Neutralize hover/transition motions for interior UI elements */
.login-wrapper .ds-card,
.login-wrapper .ds-btn,
.login-wrapper .ds-input,
.login-wrapper .feature-icon,
.login-wrapper .brand-logo-mask,
.login-wrapper .login-card-logo {
  transition: none !important;
}
.login-wrapper .ds-card:hover,
.login-wrapper .ds-btn:hover {
  transform: none !important;
  box-shadow: none !important;
}

/* Left Side - Branding */
.login-brand {
  /* Brand panel: empty/transparent with white text; no border/background */
  position: relative;
  color: #ffffff;
  background: transparent;
  border: none;
  border-radius: 0; /* square corners */
  padding: var(--space-8);
}


.brand-content {
  max-width: 500px;
}

.brand-logo {
  width: 120px;
  height: 120px;
  margin-bottom: var(--space-6);
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2));
}

/* Metallic gold school logo above the brand title, with continuous professional shine */
.brand-logo-mask {
  --logo-shine-speed: 12s;
  width: 120px;
  height: 120px;
  display: block;
  position: relative;
  margin-bottom: var(--space-6);
  /* Base metallic gold fill clipped by logo mask */
  background-image: conic-gradient(
    from 0deg,
    #8B7500 0%, #B8860B 14%, #D4AF37 28%, #FFD700 44%, #E6C200 62%, #B8860B 78%, #8B7500 92%, #D4AF37 100%
  );
  background-size: 140% 140%;
  background-position: center;
  -webkit-mask-image: url('/assets/img/logo.png');
  mask-image: url('/assets/img/logo.png');
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
  -webkit-mask-size: contain;
  mask-size: contain;
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2));
}
/* Moving glossy sweep confined to the same mask */
.brand-logo-mask::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(110deg, transparent 38%, rgba(255,255,255,.65) 50%, transparent 62%);
  background-size: 220% 220%;
  background-position: 200% 0;
  -webkit-mask-image: url('/assets/img/logo.png');
  mask-image: url('/assets/img/logo.png');
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
  -webkit-mask-size: contain;
  mask-size: contain;
  animation: goldLogoShine var(--logo-shine-speed) linear infinite;
  pointer-events: none;
}
@keyframes goldLogoShine {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
@media (prefers-reduced-motion: reduce) {
  .brand-logo-mask::after { animation: none; }
}

.brand-title {
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--space-2);
  /* Solid white title (no gold) */
  color: #ffffff;
}

.brand-subtitle {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-medium);
  margin-bottom: var(--space-6);
  color: #ffffff;
}

.brand-divider {
  width: 80px;
  height: 4px;
  background: #ffffff; /* simple white divider, no gold accent */
  border-radius: var(--radius-full);
  margin-bottom: var(--space-6);
}

.brand-description {
  font-size: var(--font-size-lg);
  line-height: var(--line-height-relaxed);
  margin-bottom: var(--space-8);
  color: #ffffff; /* description text in white */
}

.features-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.feature-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--font-size-base);
  color: #ffffff; /* make features text white */
}

.feature-icon {
  font-size: var(--font-size-xl);
  color: #ffffff; /* simple white, no gold */
}

/* Right Side - Form */
.login-form-wrapper {
  /* Place login form on the left side on wide screens */
  grid-column: 1;
  display: flex;
  justify-content: center;
}

.login-card {
  width: 100%;
  max-width: 576px; /* reverted to previous size */
  will-change: transform;
  /* Simple WHITE card (Arrow 1 requirement) */
  background: #ffffff;
  color: var(--maron-primary);
  border: 1px solid #e5e7eb;
}

.login-header {
  text-align: center;
  margin-bottom: var(--space-8);
}

.login-icon {
  font-size: 4rem;
  color: var(--maron-primary);
  margin-bottom: var(--space-4);
}

/* Security icon inside the login card header, same size as previous mask */
.login-card-logo {
  width: 72px;
  height: 72px;
  display: block;
  margin: 0 auto var(--space-4);
  color: var(--maron-primary); /* maroon icon on white card */
  font-size: 72px; /* ensure Icon component renders at same visual size */
  line-height: 72px;
}

.login-title {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--maron-primary); /* maroon title on white card */
  margin-bottom: var(--space-2);
}

.login-subtitle {
  font-size: var(--font-size-base);
  color: var(--maron-primary-700); /* maroon subtitle on white card */
  margin: 0;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-sm);
  color: var(--maron-primary); /* maroon labels on white card */
}

.label-icon {
  font-size: var(--font-size-lg);
  color: var(--maron-primary);
}

.ds-input {
  padding: var(--space-3) var(--space-4);
  border: 2px solid #e5e7eb;
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  transition: all var(--transition-fast);
}

.ds-input:focus {
  outline: none;
  border-color: var(--maron-primary);
  box-shadow: 0 0 0 3px rgba(123, 30, 30, 0.1);
}

.ds-input:disabled {
  background-color: #f3f4f6;
  cursor: not-allowed;
}

.password-input-wrapper {
  position: relative;
}

.password-input-wrapper .ds-input {
  padding-inline-end: 3rem;
}

.password-toggle {
  position: absolute;
  inset-inline-end: var(--space-3);
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #6b7280;
  cursor: pointer;
  padding: var(--space-2);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.password-toggle:hover:not(:disabled) {
  color: var(--maron-primary);
  background-color: rgba(123, 30, 30, 0.05);
}

.password-toggle:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.w-100 {
  width: 100%;
}

.login-footer {
  margin-top: var(--space-6);
  padding-top: var(--space-6);
  border-top: 1px solid #e5e7eb;
}

/* Responsive */
@media (max-width: 992px) {
  .login-wrapper {
    grid-template-columns: 1fr;
    gap: var(--space-6);
  }

  .login-brand {
    text-align: center;
    padding: var(--space-4);
  }

  .brand-content {
    max-width: 100%;
  }

  .brand-logo {
    width: 100px;
    height: 100px;
  }

  .brand-title {
    font-size: var(--font-size-3xl);
  }

  .brand-divider {
    margin-inline: auto;
  }

  .features-list {
    align-items: center;
  }
}

@media (max-width: 576px) {
  .login-container {
    padding: var(--space-3);
  }

  .brand-title {
    font-size: var(--font-size-2xl);
  }

  .login-title {
    font-size: var(--font-size-2xl);
  }
}

</style>

<style scoped>
/* Desktop ordering: brand on the right, form on the left; keep centered */
@media (min-width: 992px) {
  .login-wrapper { grid-template-areas: 'form brand'; }
  .login-form-wrapper { grid-area: form; }
  .login-brand { grid-area: brand; text-align: right; }
}
</style>

/* === Entrance animations for login panels (one-time, professional) === */
@keyframes formEnter {
  0% { opacity: 0; transform: translateX(-24px) scale(.98); filter: blur(2px); }
  60% { opacity: 1; transform: translateX(0) scale(1); filter: blur(0); }
  100% { opacity: 1; transform: none; filter: none; }
}
@keyframes brandEnter {
  0% { opacity: 0; transform: translateX(24px) scale(.98); filter: blur(2px); }
  60% { opacity: 1; transform: translateX(0) scale(1); filter: blur(0); }
  100% { opacity: 1; transform: none; filter: none; }
}

/* Apply only to the container panels, not their inner elements */
.login-form-wrapper { animation: formEnter 700ms cubic-bezier(.22,.61,.36,1) both; }
.login-brand { animation: brandEnter 720ms cubic-bezier(.22,.61,.36,1) both 60ms; }

/* Respect Reduced Motion */
@media (prefers-reduced-motion: reduce) {
  .login-form-wrapper, .login-brand { animation: none !important; }
}
