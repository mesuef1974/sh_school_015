import { defineStore } from 'pinia';
import { getMe } from '../../shared/api/client';

export interface UserProfile {
  id: number;
  username: string;
  full_name: string;
  is_superuser: boolean;
  is_staff: boolean;
  roles: string[];
  permissions: string[];
  hasTeachingAssignments: boolean;
  capabilities?: { can_manage_timetable?: boolean; can_view_general_timetable?: boolean; can_take_attendance?: boolean };
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    profile: null as UserProfile | null,
    loading: false as boolean,
    error: '' as string
  }),
  getters: {
    isAuthenticated: (state) => !!state.profile,
    roles(state) { return state.profile?.roles ?? []; },
    hasRole: (state) => (role: string) => !!state.profile?.roles?.includes(role),
    hasAnyRole: (state) => (roles: string[]) => roles.some(r => state.profile?.roles?.includes(r))
  },
  actions: {
    async loadProfile() {
      this.loading = true; this.error = '';
      try {
        const me = await getMe();
        this.profile = me;
      } catch (e: any) {
        this.error = e?.response?.data?.detail || 'تعذر تحميل الملف الشخصي';
        this.profile = null;
        throw e;
      } finally {
        this.loading = false;
      }
    },
    clear() {
      this.profile = null;
      this.error = '';
    }
  }
});