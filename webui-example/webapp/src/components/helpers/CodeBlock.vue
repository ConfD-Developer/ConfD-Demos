<!--
  Print the component's child/slot contents as a fixed-width text.
-->
<template>
  <pre :class="bgClass">{{ JSON.stringify(text, null, 2) }}</pre>
</template>

<script lang="ts" setup>import { computed } from 'vue';

const { text, greyed = true } = defineProps<{ text: unknown; greyed?: boolean }>();

const bgClass = computed(() => (greyed ? 'bg-grey-3' : ''));
</script>

<style scoped>
pre {
  white-space: pre-wrap;
  margin-top: 0px;
  margin-bottom: 0px;
}
</style>
