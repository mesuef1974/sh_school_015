import { defineStore } from "pinia";

export const useTeacherPrefs = defineStore("teacherPrefs", {
  state: () => ({
    dense: false,
    showCountdown: true,
    notifications: false,
    autoFullscreen: false,
  }),
  actions: {
    toggleDense() {
      this.dense = !this.dense;
    },
    toggleCountdown() {
      this.showCountdown = !this.showCountdown;
    },
    toggleNotifications() {
      this.notifications = !this.notifications;
    },
    toggleAutoFullscreen() {
      this.autoFullscreen = !this.autoFullscreen;
    },
  },
  persist: true as any,
});
