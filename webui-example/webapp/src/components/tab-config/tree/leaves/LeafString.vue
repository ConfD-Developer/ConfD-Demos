<template>
  <q-input
    dense
    outlined
    :readonly="readonly || !tnIsEditable"
    :rules="[leafDoDryrun]"
    hide-bottom-space
    debounce="500"
    v-model="value"
  >
    <template v-slot:append>
      <slot name="delete" />
      <leaf-type-help v-if="tnIsEditable" :context="context" :node="node" />
    </template>
  </q-input>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useTreeNode } from '../useTreeNode';
import { useServerStore } from 'src/stores/server';
import type { ConfigContext } from 'src/ts/treenodes/ConfigStateTypes';
import LeafTypeHelp from './LeafTypeHelp.vue';
import type { TreeNode } from 'src/ts/TreeNodeTypes';

const props = defineProps<{ context: ConfigContext; node: TreeNode; readonly?: boolean }>();

const { value, tnIsEditable, tnKeypath } = useTreeNode({
  context: props.context,
  node: props.node,
});
const readonly = computed(() => props.readonly === true);

const serverStore = useServerStore();

function leafDoDryrun(val: any) {
  const tasks = serverStore.tasks;
  if (!tasks) return true;
  return tasks.data.setValueDry(tnKeypath.value, val);
}
</script>
