/// <reference types="vite/client" />

import { createApp } from "vue";
import { createPinia } from "pinia";
import piniaPluginPersistedstate from "pinia-plugin-persistedstate";
import App from "./app/App.vue";
import { router } from "./app/router";
import "./styles/design-system.css";
import { i18n } from "./app/i18n";
import "./styles/maronia.css";
import "./styles/professional-tables.css";
import { VueQueryPlugin, QueryClient, VueQueryPluginOptions } from "@tanstack/vue-query";
import "vue-toastification/dist/index.css";
import Toast from "vue-toastification";