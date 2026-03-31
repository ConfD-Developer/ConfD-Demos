<!--
  a badge like component with fixed-width font label and optional tooltip
-->
<template>
  <q-badge color="grey-5" text-color="white" class="q-mx-xs">
    <code-block :text="label" :greyed="false" />
    <q-tooltip v-if="tooltip">
      <code-block :text="tooltip" :greyed="false" />
    </q-tooltip>
  </q-badge>
</template>

<script lang="ts" setup>import CodeBlock from './CodeBlock.vue';

const { label, tooltip } = defineProps<{
  label: string;
  tooltip?: string | null;
}>();
</script>
