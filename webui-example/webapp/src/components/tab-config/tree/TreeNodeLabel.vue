<template>
  <TooltipChild :when="schemaInfo !== null" :tooltip="schemaInfo">
    <div :class="colorClass">
      {{ tnLabel }}
    </div>
  </TooltipChild>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useTreeNode } from './useTreeNode';
import { resolveNested } from 'src/ts/CommonUtils';
import type { ConfigContext } from 'src/ts/treenodes/ConfigStateTypes';
import TooltipChild from 'components/helpers/TooltipChild.vue';
import type { TreeNode } from 'src/ts/TreeNodeTypes';

const props = defineProps<{ context?: ConfigContext; node: TreeNode }>();

// Prefer the typed composable; fallback to mixin import path isn't used at runtime.
const { tnLabel, tnSchema, tnKind, tnIsConfigFalse } = useTreeNode({
  context: props.context,
  node: props.node,
} as any);

const schemaInfo = computed(() => {
  const mySchema = tnSchema.value;
  const infoString = resolveNested(mySchema, ['info', 'string']);
  const gotInfo = infoString && tnKind.value !== 'list-entry';
  return gotInfo ? infoString : null;
});

const colorClass = computed(() => (tnIsConfigFalse.value ? 'text-secondary' : 'text-black'));
</script>
