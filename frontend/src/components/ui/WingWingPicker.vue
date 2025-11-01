<template>
  <div v-if="visible" class="d-flex align-items-center gap-1">
    <label class="form-label m-0 small text-muted" :for="id">الجناح:</label>
    <select :id="id" class="form-select form-select-sm w-auto" :aria-label="'اختيار الجناح'" v-model.number="localWingId" @change="onChange">
      <option :value="0">الافتراضي</option>
      <option v-for="opt in options" :key="opt.id" :value="opt.id">{{ opt.label }}</option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useWingContext } from '../../shared/composables/useWingContext';

const props = withDefaults(defineProps<{ id?: string }>(), { id: 'wing-picker' });

const { ensureLoaded, me, isSuper, setSelectedWing, selectedWingId } = useWingContext();
const localWingId = ref<number>(0);

onMounted(async () => {
  await ensureLoaded();
  localWingId.value = selectedWingId.value || 0;
});

watch(selectedWingId, (v) => {
  if ((v || 0) !== localWingId.value) localWingId.value = v || 0;
});

const options = computed(() => {
  const ids: number[] = (me.value?.wings?.ids || []).map((x: any) => Number(x));
  const names: string[] = me.value?.wings?.names || [];
  const res: { id: number; label: string }[] = [];
  for (let i = 0; i < ids.length; i++) {
    const id = ids[i];
    const raw = (names[i] || '').toString();
    // Try to extract a clean label: "<name> - <number>" → show as "رقم - اسم"
    const m1 = raw.match(/(?:الجناح|جناح)\s*(\d+)\s*[-–]?\s*(.+)/);
    if (m1) {
      res.push({ id, label: `${m1[1]} - ${m1[2]}` });
      continue;
    }
    const m2 = raw.match(/(.+)\s*[-–]\s*(?:الجناح|جناح)\s*(\d+)/);
    if (m2) {
      res.push({ id, label: `${m2[2]} - ${m2[1]}` });
      continue;
    }
    res.push({ id, label: raw || `جناح ${id}` });
  }
  // Ensure unique by id
  return res.filter((v, i, a) => a.findIndex(x => x.id === v.id) === i);
});

const visible = computed(() => {
  const count = options.value.length;
  return Boolean(isSuper.value && count > 0);
});

function onChange() {
  const id = Number(localWingId.value || 0) || null;
  setSelectedWing(id);
  // Consumers can watch selectedWingId or listen to a global event if needed
}
</script>

<style scoped>
select { min-width: 180px; }
</style>