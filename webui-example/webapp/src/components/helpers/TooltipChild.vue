<!--
  Simple wrapper for adding mouse hover tooltip for a child/slot contents,
  conditioned to show on specific condition...
-->
<template>
  <div>
    <slot />
    <q-tooltip
      v-if="when"
      :delay="props.delay ?? 500"
    >
      {{ props.tooltip }}
    </q-tooltip>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  tooltip: unknown
  when?: boolean
  delay?: number
}>()
</script>
