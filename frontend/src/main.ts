import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './app/App.vue';
import { router } from './app/router';
import './styles/maronia.css';
import { VueQueryPlugin, QueryClient, VueQueryPluginOptions } from '@tanstack/vue-query';
import 'vue-toastification/dist/index.css';
import Toast from 'vue-toastification';

const app = createApp(App);
app.use(createPinia());

// Vue Query setup (sane defaults for dev)
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, retry: 1, staleTime: 60_000 }
  }
});
app.use(VueQueryPlugin, { queryClient } as VueQueryPluginOptions);

// Toast plugin (Arabic RTL-friendly defaults)
app.use(Toast, { rtl: true, position: 'top-center', timeout: 3000 });

app.use(router);
app.mount('#app');