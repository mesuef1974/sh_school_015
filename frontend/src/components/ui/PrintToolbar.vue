<template>
  <div class="print-toolbar d-flex flex-wrap align-items-center gap-2">
    <div class="input-group input-group-sm" style="width:auto">
      <span class="input-group-text">الاتجاه</span>
      <select class="form-select" v-model="orientation">
        <option value="portrait">طولي</option>
        <option value="landscape">عرضي</option>
      </select>
    </div>
    <div class="input-group input-group-sm" style="width:auto">
      <span class="input-group-text">الهامش</span>
      <select class="form-select" v-model.number="margin">
        <option :value="0.5">0.5 سم</option>
        <option :value="1">1 سم</option>
        <option :value="1.5">1.5 سم</option>
        <option :value="2">2 سم</option>
      </select>
    </div>
    <div class="input-group input-group-sm" style="width:auto">
      <span class="input-group-text">المقياس</span>
      <select class="form-select" v-model.number="scale">
        <option :value="50">50%</option>
        <option :value="60">60%</option>
        <option :value="70">70%</option>
        <option :value="80">80%</option>
        <option :value="90">90%</option>
        <option :value="100">100%</option>
        <option :value="110">110%</option>
      </select>
    </div>
    <div class="input-group input-group-sm" style="width:auto">
      <span class="input-group-text">الكثافة</span>
      <select class="form-select" v-model="density">
        <option value="normal">عادية</option>
        <option value="compact">مضغوطة</option>
      </select>
    </div>

    <div class="form-check form-check-inline">
      <input class="form-check-input" type="checkbox" id="pt-clean" v-model="clean" />
      <label class="form-check-label" for="pt-clean">وضع نظيف</label>
    </div>
    <div class="form-check form-check-inline">
      <input class="form-check-input" type="checkbox" id="pt-grid" v-model="grid" />
      <label class="form-check-label" for="pt-grid">إطار الجدول</label>
    </div>

    <div class="ms-auto d-flex gap-2">
      <button class="btn btn-outline-secondary btn-sm" @click="printPortrait">
        <Icon icon="solar:document-bold-duotone" class="me-1"/> طولي
      </button>
      <button class="btn btn-outline-secondary btn-sm" @click="printLandscape">
        <Icon icon="solar:document-add-bold-duotone" class="me-1"/> عرضي
      </button>
      <button class="btn btn-primary btn-sm" @click="printNow">
        <Icon icon="solar:printer-2-bold-duotone" class="me-1"/> طباعة
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { Icon } from "@iconify/vue";

// Local UI state (could be wired to prefs later if needed)
const orientation = ref<'portrait'|'landscape'>('portrait');
const margin = ref<number>(1);
const scale = ref<number>(100);
const density = ref<'normal'|'compact'>('normal');
const clean = ref<boolean>(false);
const grid = ref<boolean>(true);

function buildBodyClasses(): string[] {
  const classes: string[] = [];
  // density
  if (density.value === 'compact') classes.push('print-compact');
  // clean mode optionally hides/minimizes non-essential chrome if CSS defines it
  if (clean.value) classes.push('print-clean');
  // grid toggle: when false, add class to remove borders
  if (!grid.value) classes.push('print-no-grid');
  // scale mapping - extended down to 50%
  if (scale.value === 50) classes.push('print-scale-50');
  else if (scale.value === 60) classes.push('print-scale-60');
  else if (scale.value === 70) classes.push('print-scale-70');
  else if (scale.value === 80) classes.push('print-scale-80');
  else if (scale.value === 90) classes.push('print-scale-90');
  else if (scale.value === 110) classes.push('print-scale-110');
  else classes.push('print-scale-100');
  return classes;
}

function doPrint(or?: 'portrait'|'landscape') {
  const opts: any = {
    orientation: or || orientation.value,
    marginCm: margin.value,
    addBodyClasses: buildBodyClasses(),
  };
  // @ts-ignore - provided globally in main.ts
  const pm = window.printManager || (globalThis as any).printManager || ({});
  if (pm && typeof pm.print === 'function') {
    pm.print(opts);
  } else if (typeof window !== 'undefined' && window.print) {
    window.print();
  }
}

function printNow() { doPrint(); }
function printPortrait() { doPrint('portrait'); }
function printLandscape() { doPrint('landscape'); }

</script>

<style scoped>
.print-toolbar { direction: rtl; }
</style>