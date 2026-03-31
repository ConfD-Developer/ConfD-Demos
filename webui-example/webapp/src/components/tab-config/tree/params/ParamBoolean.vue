<template>
  <q-checkbox dense v-model="model" />
</template>

<script setup lang="ts">
import type { YangSchemaNode } from 'src/ts/YangSchemaTypes';

defineProps<{ schema: YangSchemaNode }>();
const model = defineModel<boolean>();
</script>
