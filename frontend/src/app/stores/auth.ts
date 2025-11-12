import { defineStore } from "pinia";
import { getMe } from "../../shared/api/client";

export interface UserProfile {
  id: number;
  username: string;
  full_name: string;
  is_superuser: boolean;
  is_staff: boolean;
  roles: string[];
  permissions: string[];
  hasTeachingAssignments: boolean;
  capabilities?: {
    can_manage_timetable?: boolean;
    can_view_general_timetable?: boolean;
    can_take_attendance?: boolean;
    // extended
    discipline_l1?: boolean;
    discipline_l2?: boolean;
    exams_manage?: boolean;
    health_can_view_masked?: boolean;
    health_can_unmask?: boolean;
    can_propose_irreversible?: boolean;
    can_approve_irreversible?: boolean;
  };
  primary_route?: string;
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    profile: null as UserProfile | null,
    loading: false as boolean,
    error: "" as string,
  }),
  getters: {
    isAuthenticated: (state) => !!state.profile,
    roles(state) {
      return state.profile?.roles ?? [];
    },
    hasRole: (state) => (role: string) => !!state.profile?.roles?.includes(role),
    hasAnyRole: (state) => (roles: string[]) =>
      roles.some((r) => state.profile?.roles?.includes(r)),
    capabilities(state) {
      return state.profile?.capabilities ?? {};
    },
    can: (state) => (key: keyof NonNullable<UserProfile['capabilities']>) => {
      const caps = state.profile?.capabilities as any;
      return !!(caps && caps[key]);
    },
  },
  actions: {
    async loadProfile() {
      this.loading = true;
      this.error = "";
      try {
        const me = await getMe();
        this.profile = me;
      } catch (e: any) {
        this.error = e?.response?.data?.detail || "تعذر تحميل الملف الشخصي";
        this.profile = null;
        throw e;
      } finally {
        this.loading = false;
      }
    },
    clear() {
      this.profile = null;
      this.error = "";
    },
  },
});
