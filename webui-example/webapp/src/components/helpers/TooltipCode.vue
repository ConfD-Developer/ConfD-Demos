<!--
  wrapper for adding a fixed font width ("code") style tooltip
  to child/slot contents
-->
<template>
  <div>
    <slot />
    <q-tooltip>
      <code-block :greyed="false" :text="tooltip" />
    </q-tooltip>
  </div>
</template>

<script lang="ts" setup>
import CodeBlock from './CodeBlock.vue';

const { tooltip } = defineProps<{ tooltip: string }>();
</script>
