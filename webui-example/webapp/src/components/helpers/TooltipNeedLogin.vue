<!--
  Simple wrapper for slot contents - add mouse tooltip
  about ConfD login needed...
-->
<template>
  <tooltip-child tooltip="Connect to device!" :when="!connected">
    <slot />
  </tooltip-child>
</template>

<script lang="ts" setup>import { storeToRefs } from 'pinia';
import { useServerStore } from 'src/stores/server';
import TooltipChild from './TooltipChild.vue';

const { connected } = storeToRefs(useServerStore());
</script>
