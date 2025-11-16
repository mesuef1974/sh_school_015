<template>
  <nav class="teacher-menu" aria-label="قائمة المعلم">
    <ul class="nav nav-pills flex-wrap gap-2">
      <li class="nav-item">
        <RouterLink class="nav-link" :class="activeClass('/')" to="/">
          <i class="bi bi-house-door"></i>
          <span>الرئيسية</span>
        </RouterLink>
      </li>
      <li class="nav-item" v-if="canSeeTeacher">
        <RouterLink
          class="nav-link"
          :class="activeClass('/attendance/teacher')"
          to="/attendance/teacher"
        >
          <i class="bi bi-clipboard-check"></i>
          <span>تسجيل الغياب</span>
        </RouterLink>
      </li>
      <li class="nav-item" v-if="canSeeTeacher">
        <RouterLink
          class="nav-link"
          :class="activeClass('/timetable/teacher')"
          to="/timetable/teacher"
        >
          <i class="bi bi-calendar2-week"></i>
          <span>جدولي</span>
        </RouterLink>
      </li>
      <li class="nav-item" v-if="canSeeTeacher">
        <RouterLink
          class="nav-link"
          :class="activeClass('/attendance/teacher/history')"
          to="/attendance/teacher/history"
        >
          <i class="bi bi-clock-history"></i>
          <span>سجل الغياب</span>
        </RouterLink>
      </li>
    </ul>
  </nav>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useAuthStore } from "../../../app/stores/auth";

const route = useRoute();
const auth = useAuthStore();
const canSeeTeacher = computed(() => {
  const roles = auth.profile?.roles || [];
  const isTeacher = roles.includes("teacher");
  const isCoordinator = roles.includes("subject_coordinator");
  const byAssignment = !!auth.profile?.hasTeachingAssignments;
  const isSuper = !!auth.profile?.is_superuser;
  return isTeacher || isCoordinator || byAssignment || isSuper;
});

function activeClass(prefix: string) {
  // Mark active if current path starts with the target prefix
  return route.path === prefix || route.path.startsWith(prefix + "/") ? "active" : "";
}
</script>

<style scoped>
.teacher-menu {
  margin-bottom: 0.75rem;
}
.nav-link {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
.nav-link.active {
  background: var(--maron-primary);
  border-color: var(--maron-primary);
}
</style>
