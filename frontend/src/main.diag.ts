import { createApp, defineComponent } from "vue";

// Minimal diagnostic bootstrap to rule out Vite/Vue mounting issues.
const Diag = defineComponent({
  name: "DiagRoot",
  template: `<div style="padding:1rem; font-family: system-ui, sans-serif">
    <h3>BOOT OK</h3>
    <p>Vue mounted successfully (diagnostic entry). If the normal entry shows a white screen, the issue is in src/main.ts or one of its imports.</p>
  </div>`,
});

const app = createApp(Diag);

// Surface any runtime errors clearly
if (import.meta.env.DEV) {
  app.config.errorHandler = (err, instance, info) => {
    console.error("[Diag VueError]", err, info, instance);
    try {
      const el = document.querySelector("#app");
      if (el) {
        const pre = document.createElement("pre");
        pre.className = "fallback-error";
        pre.textContent = `[Diag VueError] ${String(err)}\ninfo: ${String(info ?? "")}\n`;
        el.prepend(pre);
      }
    } catch {}
  };
  window.addEventListener("error", (e) => {
    console.error("[Diag WindowError]", (e as any).error || (e as any).message);
  });
  window.addEventListener("unhandledrejection", (e) => {
    console.error("[Diag UnhandledRejection]", (e as any).reason);
  });
}

try {
  app.mount("#app");
} catch (e) {
  console.error("[Diag MountError]", e);
  try {
    const el = document.querySelector("#app");
    if (el) {
      const pre = document.createElement("pre");
      pre.className = "fallback-error";
      pre.textContent = `[Diag MountError] ${String(e)}`;
      el.prepend(pre);
    }
  } catch {}
}
