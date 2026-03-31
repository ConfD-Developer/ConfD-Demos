<template>
  <q-select dense outlined options-dense :options="enumOptions" v-model="model" />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { YangSchemaNode } from 'src/ts/YangSchemaTypes';

const model = defineModel<string>();
const props = defineProps<{ schema: YangSchemaNode }>();

const enumOptions = computed(() => {
  const enumsArr = props.schema?.enumeration ?? [];
  const result: string[] = [];
  for (const item of enumsArr) {
    if (typeof item?.label === 'string') {
      result.push(item.label);
    }
  }
  return result;
});
</script>
