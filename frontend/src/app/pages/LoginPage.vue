<template>
  <div class="container py-4">
    <div class="row justify-content-center">
      <div class="col-12 col-md-6">
        <div class="card p-4 shadow-sm">
          <h1 class="h4 mb-3 text-center">تسجيل الدخول</h1>
          <form @submit.prevent="onSubmit">
            <div class="mb-3">
              <label class="form-label">اسم المستخدم</label>
              <input v-model="username" type="text" class="form-control" required />
            </div>
            <div class="mb-3">
              <label class="form-label">كلمة المرور</label>
              <input v-model="password" type="password" class="form-control" required />
            </div>
            <div class="d-grid">
              <button class="btn btn-maron" :disabled="loading">دخول</button>
            </div>
            <p class="text-danger mt-3" v-if="error">{{ error }}</p>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { login } from '../../shared/api/client';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const username = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');

async function onSubmit() {
  loading.value = true; error.value = '';
  try {
    await login(username.value, password.value);
    try { await auth.loadProfile(); } catch { /* ignore for now */ }
    const next = (route.query.next as string) || '/';
    router.replace(next);
  } catch (e: any) {
    if (!e?.response) {
      error.value = 'الخادم غير متاح الآن. تأكد من تشغيل الباك-إند ثم أعد المحاولة.';
    } else {
      error.value = e?.response?.data?.detail || 'بيانات الدخول غير صحيحة';
    }
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.card { border-radius: .75rem; }
</style>