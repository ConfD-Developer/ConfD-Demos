<template>
  <div class="row">
    <q-checkbox dense :label="myLabel" :disable="readonly || !tnIsEditable" v-model="value" />
    <q-space />
    <slot name="delete" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useTreeNode } from '../useTreeNode';
import type { ConfigContext } from 'src/ts/treenodes/ConfigStateTypes';
import type { TreeNode } from 'src/ts/TreeNodeTypes';

const props = defineProps<{ context: ConfigContext; node: TreeNode; readonly?: boolean }>();

const { value, tnIsTypeEmpty, tnIsEditable } = useTreeNode({ context: props.context, node: props.node });
const readonly = computed(() => props.readonly === true);

const myLabel = computed(() => {
  if (tnIsTypeEmpty.value) return undefined;
  const val = value.value;
  const notSet = val === null || val === undefined;
  return notSet ? 'not set' : String(val);
});
</script>
