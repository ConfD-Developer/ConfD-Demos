<!--
  Interface header for collapsible QTree.
  Adds control buttons and text filter input for quicker tree nodes navigation.
-->
<template>
  <q-input v-model="model" dense :label="props.filterLabel" :disable="props.disable">
    <template v-slot:prepend>
      <q-icon name="search" />
    </template>
    <template v-slot:append>
      <div class="row q-gutter-x-sm">
        <TooltipChild v-if="model !== ''" tooltip="clear filter">
          <q-btn dense size="xs" icon="clear" @click="model = ''" />
        </TooltipChild>
        <TooltipChild tooltip="expand all">
          <q-btn icon="unfold_more" dense size="xs" :disable="props.disable" @click="emit('expandAll')" />
        </TooltipChild>
        <TooltipChild tooltip="collapse all">
          <q-btn icon="unfold_less" size="xs" dense :disable="props.disable" @click="emit('collapseAll')" />
        </TooltipChild>
        <TooltipChild v-if="props.warning" :tooltip="props.warning">
          <q-icon name="warning" />
        </TooltipChild>
      </div>
    </template>
  </q-input>
</template>

<script setup lang="ts">
import TooltipChild from 'components/helpers/TooltipChild.vue';

const props = defineProps<{
  disable?: boolean;
  filterLabel?: string;
  warning?: string;
}>();

const model = defineModel<string>();

const emit = defineEmits(['expandAll', 'collapseAll']);
</script>
