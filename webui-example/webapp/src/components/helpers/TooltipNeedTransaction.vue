<!--
  Simple wrapper for slot contents - add mouse tooltip
  about ConfD transaction needed...
-->
<template>
  <tooltip-child tooltip="Start a transaction!" :when="!hasTrans">
    <slot />
  </tooltip-child>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { useTransactionStore } from 'src/stores/transaction';
import TooltipChild from './TooltipChild.vue';

const { hasTrans } = storeToRefs(useTransactionStore());
</script>
