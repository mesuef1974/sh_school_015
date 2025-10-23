<template>
  <div class="login-container">
    <div class="login-wrapper">
      <!-- Left Side - Branding -->
      <div
        class="login-brand"
        v-motion
        :initial="{ opacity: 0, x: -100 }"
        :enter="{ opacity: 1, x: 0, transition: { duration: 600 } }"
      >
        <div class="brand-content">
          <span class="brand-logo-mask" aria-hidden="true"></span>
          <h1 class="brand-title">مدرسة الشحانية</h1>
          <p class="brand-subtitle">الإعدادية الثانوية للبنين</p>
          <div class="brand-divider"></div>
          <p class="brand-description">
            منصة الإدارة المدرسية الذكية
            <br />
            إدارة شاملة وتقارير فورية
          </p>

          <!-- Features -->
          <div class="features-list">
            <div class="feature-item">
              <Icon icon="solar:check-circle-bold-duotone" class="feature-icon" />
              <span>إدارة الحضور والغياب</span>
            </div>
            <div class="feature-item">
              <Icon icon="solar:check-circle-bold-duotone" class="feature-icon" />
              <span>تقارير تفصيلية فورية</span>
            </div>
            <div class="feature-item">
              <Icon icon="solar:check-circle-bold-duotone" class="feature-icon" />
              <span>واجهة سهلة الاستخدام</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Side - Login Form -->
      <div
        class="login-form-wrapper"
        v-motion
        :initial="{ opacity: 0, x: 100 }"
        :enter="{ opacity: 1, x: 0, transition: { duration: 600, delay: 200 } }"
      >
        <DsCard
          class="login-card"
          :animate="false"
          v-motion
          :initial="{ opacity: 0, y: 24, scale: 0.96 }"
          :enter="{ opacity: 1, y: 0, scale: 1, transition: { duration: 500, easing: 'cubic-bezier(0.22, 1, 0.36, 1)', delay: 120 } }"
        >
          <div class="login-header">
            <span class="login-card-logo" aria-hidden="true"></span>
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
              icon="solar:login-3-bold-duotone"
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

    const next = (route.query.next as string) || '/';
    router.replace(next);
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
  height: calc(100vh - var(--app-header-h) - var(--app-footer-h));
  display: flex;
  align-items: center;
  justify-content: center;
  /* Background image as requested */
  background-image: url('/assets/img/portal_bg.png');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  padding: 0;
  overflow: hidden; /* prevent scrollbars on the login page */
}

.login-wrapper {
  max-width: 1200px;
  width: 100%;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-8);
  align-items: center;
  /* Backdrop card behind both the branding and the login panel */
  position: relative;
  border-radius: 0; /* square corners */
  border: 5px solid transparent; /* 5px golden frame */
  /* Metallic gold border (border-box) only; maroon fill provided by ::after */
  background:
    linear-gradient(135deg, #7a5e2e, #cdaa2c, #b8890b, #fff2b2, #b8890b, #d4af37, #7a5e2e) border-box;
  -webkit-backdrop-filter: blur(50px);
  backdrop-filter: blur(50px); /* 50px blur */
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.25);
  padding: var(--space-8);
}

/* Animated glossy shine over the golden frame */

/* Inner maroon fill only (no shine) */
.login-wrapper::after {
  content: "";
  position: absolute;
  inset: 5px; /* match the 5px golden border */
  border-radius: inherit;
  pointer-events: none;
  background: linear-gradient(rgba(128, 0, 0, 0.9), rgba(128, 0, 0, 0.9));
}

/* Ensure all children sit above the ::after cover */
.login-wrapper > * {
  position: relative;
  z-index: 1;
}

/* Left Side - Branding */
.login-brand {
  color: var(--maron-primary);
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

/* Maroon-tinted school logo above the brand title */
.brand-logo-mask {
  width: 120px;
  height: 120px;
  display: block;
  margin-bottom: var(--space-6);
  background-color: #ffffff; /* logo in white */
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

.brand-title {
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--space-2);
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
  background: var(--maron-accent);
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
  color: #f5d08a; /* keep a warm accent that contrasts on maroon */
}

/* Right Side - Form */
.login-form-wrapper {
  display: flex;
  justify-content: center;
}

.login-card {
  width: 100%;
  max-width: 480px;
  transform: scale(0.9);
  transform-origin: center;
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

/* Maroon school logo inside the login card header */
.login-card-logo {
  width: 72px;
  height: 72px;
  display: block;
  margin: 0 auto var(--space-4);
  background-color: var(--maron-primary);
  -webkit-mask-image: url('/assets/img/logo.png');
  mask-image: url('/assets/img/logo.png');
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
  -webkit-mask-size: contain;
  mask-size: contain;
}

.login-title {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--maron-primary);
  margin-bottom: var(--space-2);
}

.login-subtitle {
  font-size: var(--font-size-base);
  color: #6b7280;
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
  color: #374151;
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