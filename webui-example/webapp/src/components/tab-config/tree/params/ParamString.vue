<template>
  <q-input dense outlined v-model="model" @click.stop />
</template>

<script setup lang="ts">
import type { YangSchemaNode } from 'src/ts/YangSchemaTypes';

defineProps<{ schema: YangSchemaNode }>();
const model = defineModel<string>();
</script>
