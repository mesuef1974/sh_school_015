<template>
  <div class="date-picker-dmy" :class="wrapperClass">
    <label v-if="label" class="form-label" :for="id">{{ label }}</label>
    <div class="d-flex align-items-center gap-2">
      <input
        :id="id"
        :aria-label="ariaLabel || label || 'اختيار التاريخ'"
        type="date"
        class="form-control"
        :class="inputClass"
        :value="modelValue"
        @input="onInput"
        @change="onChange"
        dir="ltr"
      />
      <slot name="after"></slot>
    </div>
    <small v-if="modelValue" class="text-muted d-block mt-1">
      {{ helperPrefix }} {{ formatted }}
    </small>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatDateDMY } from '../../shared/utils/date'

interface Props {
  modelValue: string | null | undefined
  id?: string
  label?: string
  ariaLabel?: string
  inputClass?: string
  wrapperClass?: string
  helperPrefix?: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: string | null): void
  (e: 'change', v: string | null): void
}>()

const formatted = computed(() => formatDateDMY(props.modelValue || ''))

function onInput(e: Event) {
  const v = (e.target as HTMLInputElement).value || null
  emit('update:modelValue', v)
}
function onChange(e: Event) {
  const v = (e.target as HTMLInputElement).value || null
  emit('change', v)
}
</script>

<style scoped>
.date-picker-dmy .form-control {
  width: auto;
}
</style>
