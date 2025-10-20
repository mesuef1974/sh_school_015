<template>
  <div class="profile-page">
    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <div class="loading-spinner">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">جاري التحميل...</span>
        </div>
      </div>
      <p class="loading-text">جاري تحميل بياناتك...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <div class="error-icon">
        <i class="bi bi-exclamation-triangle"></i>
      </div>
      <h3>حدث خطأ في تحميل البيانات</h3>
      <p>{{ error }}</p>
      <button @click="refetchProfile" class="btn btn-primary btn-retry">
        <i class="bi bi-arrow-clockwise me-2"></i>
        إعادة المحاولة
      </button>
    </div>

    <!-- Success State -->
    <section v-else class="profile-content">
      <!-- Welcome Header -->
      <header
        v-motion
        :initial="{ opacity: 0, y: -30 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 600, delay: 100 } }"
        class="welcome-header"
      >
        <div class="welcome-badge">
          <img :src="logoSrc" alt="شعار المدرسة" class="school-logo" />
          <div class="welcome-text">
            <div class="greeting">{{ salutation }}</div>
            <div class="user-name">{{ name }}</div>
          </div>
        </div>
        <div class="header-decoration"></div>
      </header>

      <!-- Profile Card -->
      <main
        v-motion
        :initial="{ opacity: 0, y: 30 }"
        :enter="{ opacity: 1, y: 0, transition: { duration: 600, delay: 200 } }"
        class="profile-card"
      >
        <!-- Card Header -->
        <div class="profile-header">
          <div class="profile-title">
            <i class="bi bi-person-circle profile-icon"></i>
            <h1>الملف الشخصي</h1>
          </div>
          <button @click="refetchProfile" class="btn-refresh" :disabled="refreshing">
            <i class="bi bi-arrow-clockwise" :class="{ 'spinning': refreshing }"></i>
            <span class="tooltip-text">تحديث البيانات</span>
          </button>
        </div>

        <!-- Profile Information Grid -->
        <div class="profile-grid">
          <!-- Personal Information Section -->
          <div class="info-section">
            <h2 class="section-title">
              <i class="bi bi-person-lines-fill"></i>
              المعلومات الشخصية
            </h2>

            <div class="info-row">
              <div class="info-item" v-motion :initial="{ opacity: 0, x: -20 }" :enter="{ opacity: 1, x: 0, transition: { duration: 500, delay: 300 } }">
                <div class="info-label">
                  <i class="bi bi-person"></i>
                  <span>الاسم الكامل</span>
                </div>
                <div class="info-value">{{ profile?.full_name || 'غير متوفر' }}</div>
              </div>

              <div class="info-item" v-motion :initial="{ opacity: 0, x: -20 }" :enter="{ opacity: 1, x: 0, transition: { duration: 500, delay: 350 } }">
                <div class="info-label">
                  <i class="bi bi-envelope"></i>
                  <span>البريد الإلكتروني</span>
                </div>
                <div class="info-value">{{ profile?.email || 'غير متوفر' }}</div>
              </div>
            </div>

            <div class="info-row">
              <div class="info-item" v-motion :initial="{ opacity: 0, x: -20 }" :enter="{ opacity: 1, x: 0, transition: { duration: 500, delay: 400 } }">
                <div class="info-label">
                  <i class="bi bi-telephone"></i>
                  <span>رقم الهاتف</span>
                </div>
                <div class="info-value">{{ profile?.phone || 'غير متوفر' }}</div>
              </div>

              <div class="info-item" v-motion :initial="{ opacity: 0, x: -20 }" :enter="{ opacity: 1, x: 0, transition: { duration: 500, delay: 450 } }">
                <div class="info-label">
                  <i class="bi bi-calendar3"></i>
                  <span>تاريخ الميلاد</span>
                </div>
                <div class="info-value">{{ formatDate(profile?.birth_date) || 'غير متوفر' }}</div>
              </div>
            </div>
          </div>

          <!-- Work Information Section -->
          <div class="info-section">
            <h2 class="section-title">
              <i class="bi bi-briefcase-fill"></i>
              معلومات العمل
            </h2>

            <div class="info-row">
              <div class="info-item" v-motion :initial="{ opacity: 0, x: -20 }" :enter="{ opacity: 1, x: 0, transition: { duration: 500, delay: 500 } }">
                <div class="info-label">
                  <i class="bi bi-briefcase"></i>
                  <span>المنصب</span>
                </div>
                <div class="info-value">{{ profile?.position || 'غير متوفر' }}</div>
              </div>

              <div class="info-item" v-motion :initial="{ opacity: 0, x: -20 }" :enter="{ opacity: 1, x: 0, transition: { duration: 500, delay: 550 } }">
                <div class="info-label">
                  <i class="bi bi-building"></i>
                  <span>القسم</span>
                </div>
                <div class="info-value">{{ profile?.department || 'غير متوفر' }}</div>
              </div>
            </div>

            <div class="info-row">
              <div class="info-item" v-motion :initial="{ opacity: 0, x: -20 }" :enter="{ opacity: 1, x: 0, transition: { duration: 500, delay: 600 } }">
                <div class="info-label">
                  <i class="bi bi-calendar-check"></i>
                  <span>تاريخ الانضمام</span>
                </div>
                <div class="info-value">{{ formatDate(profile?.date_joined) || 'غير متوفر' }}</div>
              </div>

              <div class="info-item" v-motion :initial="{ opacity: 0, x: -20 }" :enter="{ opacity: 1, x: 0, transition: { duration: 500, delay: 650 } }">
                <div class="info-label">
                  <i class="bi bi-shield-check"></i>
                  <span>حالة الحساب</span>
                </div>
                <div class="info-value">
                  <span class="status-badge status-active">
                    <i class="bi bi-check-circle"></i>
                    نشط
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Quick Actions -->
        <div class="quick-actions" v-motion :initial="{ opacity: 0, y: 20 }" :enter="{ opacity: 1, y: 0, transition: { duration: 500, delay: 700 } }">
          <h2 class="section-title">
            <i class="bi bi-lightning-charge-fill"></i>
            إجراءات سريعة
          </h2>
          <div class="actions-grid">
            <button class="action-btn" @click="changePassword">
              <i class="bi bi-key"></i>
              <span>تغيير كلمة المرور</span>
            </button>
            <button class="action-btn" @click="updateProfile">
              <i class="bi bi-pencil-square"></i>
              <span>تعديل البيانات</span>
            </button>
            <button class="action-btn" @click="viewActivity">
              <i class="bi bi-activity"></i>
              <span>سجل النشاط</span>
            </button>
          </div>
        </div>
      </main>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useMotion } from '@vueuse/motion'
import { useAuthStore } from '../stores/authStore'
import { useAPI } from '../composables/useAPI'
import { toast } from 'vue3-toastify'

const authStore = useAuthStore()
const { fetchData } = useAPI()

// Reactive state
const profile = ref(null)
const loading = ref(true)
const error = ref(null)
const refreshing = ref(false)

// Computed properties
const salutation = computed(() => {
  const hour = new Date().getHours()
  if (hour >= 5 && hour < 12) return 'صباح الخير'
  if (hour >= 12 && hour < 17) return 'مساء الخير'
  if (hour >= 17 && hour < 21) return 'مساء الخير'
  return 'أهلاً وسهلاً'
})

const name = computed(() => profile.value?.full_name || authStore.user?.username || 'المستخدم')

const logoSrc = computed(() => {
  return new URL('../assets/logo.png', import.meta.url).href
})

// Methods
const formatDate = (dateString) => {
  if (!dateString) return null
  const date = new Date(dateString)
  return date.toLocaleDateString('ar-EG', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

const fetchProfile = async () => {
  try {
    loading.value = true
    error.value = null
    profile.value = await fetchData('/api/me/')
  } catch (err) {
    console.error('Error fetching profile:', err)
    error.value = 'تعذر تحميل بيانات الملف الشخصي. يرجى المحاولة مرة أخرى.'
    toast.error('خطأ في تحميل البيانات')
  } finally {
    loading.value = false
  }
}

const refetchProfile = async () => {
  refreshing.value = true
  await fetchProfile()
  refreshing.value = false
  if (!error.value) {
    toast.success('تم تحديث البيانات بنجاح')
  }
}

const changePassword = () => {
  toast.info('سيتم إضافة هذه الميزة قريباً')
}

const updateProfile = () => {
  toast.info('سيتم إضافة هذه الميزة قريباً')
}

const viewActivity = () => {
  toast.info('سيتم إضافة هذه الميزة قريباً')
}

// Lifecycle
onMounted(() => {
  fetchProfile()
})
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  padding: 1.5rem;
}

/* Loading State */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
}

.loading-spinner {
  margin-bottom: 1.5rem;
}

.loading-spinner .spinner-border {
  width: 3rem;
  height: 3rem;
}

.loading-text {
  font-size: 1.1rem;
  color: #6c757d;
  margin: 0;
}

/* Error State */
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
  background: white;
  border-radius: 16px;
  padding: 3rem 2rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.error-icon {
  font-size: 4rem;
  color: #dc3545;
  margin-bottom: 1.5rem;
}

.error-container h3 {
  color: #dc3545;
  margin-bottom: 1rem;
}

.error-container p {
  color: #6c757d;
  margin-bottom: 2rem;
}

.btn-retry {
  padding: 0.75rem 2rem;
  border-radius: 50px;
  font-weight: 600;
  transition: all 0.3s ease;
}

.btn-retry:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(0, 123, 255, 0.3);
}

/* Profile Content */
.profile-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* Welcome Header */
.welcome-header {
  position: relative;
  background: linear-gradient(135deg, #8B4513 0%, #A0522D 100%);
  border-radius: 20px;
  padding: 2rem;
  color: white;
  overflow: hidden;
}

.welcome-badge {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  position: relative;
  z-index: 2;
}

.school-logo {
  height: 64px;
  width: 64px;
  object-fit: contain;
  filter: brightness(0) invert(1);
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 8px;
}

.welcome-text {
  flex: 1;
}

.greeting {
  font-size: 1.1rem;
  opacity: 0.9;
  margin-bottom: 0.5rem;
}

.user-name {
  font-size: 1.8rem;
  font-weight: 700;
  white-space: nowrap;
}

.header-decoration {
  position: absolute;
  top: -50%;
  right: -10%;
  width: 200px;
  height: 200px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 50%;
  z-index: 1;
}

/* Profile Card */
.profile-card {
  background: white;
  border-radius: 20px;
  padding: 2rem;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(139, 69, 19, 0.1);
}

.profile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 2px solid #f8f9fa;
}

.profile-title {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.profile-icon {
  font-size: 2.5rem;
  color: #8B4513;
}

.profile-title h1 {
  font-size: 2rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0;
}

.btn-refresh {
  position: relative;
  background: rgba(139, 69, 19, 0.1);
  border: 2px solid rgba(139, 69, 19, 0.2);
  color: #8B4513;
  padding: 0.75rem;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 1.2rem;
}

.btn-refresh:hover:not(:disabled) {
  background: #8B4513;
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(139, 69, 19, 0.3);
}

.btn-refresh:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.tooltip-text {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  background: #2c3e50;
  color: white;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.8rem;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s;
  margin-bottom: 0.5rem;
}

.btn-refresh:hover .tooltip-text {
  opacity: 1;
}

/* Profile Grid */
.profile-grid {
  display: grid;
  gap: 2.5rem;
}

.info-section {
  background: #f8f9fa;
  border-radius: 16px;
  padding: 2rem;
  border: 1px solid rgba(139, 69, 19, 0.1);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.3rem;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 1.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid rgba(139, 69, 19, 0.1);
}

.section-title i {
  color: #8B4513;
  font-size: 1.4rem;
}

.info-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-item {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  border: 1px solid #e9ecef;
  transition: all 0.3s ease;
}

.info-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border-color: rgba(139, 69, 19, 0.2);
}

.info-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 600;
  color: #495057;
  margin-bottom: 0.75rem;
  font-size: 0.95rem;
}

.info-label i {
  color: #8B4513;
  font-size: 1.1rem;
}

.info-value {
  font-size: 1.1rem;
  color: #2c3e50;
  font-weight: 500;
  word-break: break-word;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 50px;
  font-size: 0.9rem;
  font-weight: 600;
}

.status-active {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

/* Quick Actions */
.quick-actions {
  background: linear-gradient(135deg, rgba(139, 69, 19, 0.05) 0%, rgba(160, 82, 45, 0.05) 100%);
  border-radius: 16px;
  padding: 2rem;
  border: 1px solid rgba(139, 69, 19, 0.1);
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: white;
  border: 2px solid rgba(139, 69, 19, 0.2);
  color: #8B4513;
  padding: 1rem 1.5rem;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 600;
  text-decoration: none;
}

.action-btn:hover {
  background: #8B4513;
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(139, 69, 19, 0.3);
}

.action-btn i {
  font-size: 1.2rem;
}

/* Responsive Design */
@media (max-width: 768px) {
  .profile-page {
    padding: 1rem;
  }

  .welcome-header {
    padding: 1.5rem;
  }

  .welcome-badge {
    gap: 1rem;
  }

  .school-logo {
    height: 48px;
    width: 48px;
  }

  .user-name {
    font-size: 1.4rem;
  }

  .profile-card {
    padding: 1.5rem;
  }

  .profile-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .profile-title h1 {
    font-size: 1.5rem;
  }

  .info-section {
    padding: 1.5rem;
  }

  .info-row {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .info-item {
    padding: 1rem;
  }

  .actions-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .welcome-badge {
    flex-direction: column;
    text-align: center;
  }

  .user-name {
    white-space: normal;
    text-align: center;
  }
}

/* Accessibility */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .profile-card {
    border: 2px solid #2c3e50;
  }

  .info-item {
    border: 2px solid #8B4513;
  }
}
</style>