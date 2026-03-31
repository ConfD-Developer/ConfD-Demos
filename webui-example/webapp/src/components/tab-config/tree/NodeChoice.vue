<template>
  <div class="row col-12 items-baseline">
    <div class="row col-4">
      <tree-node-label :node="node" :context="context" />
    </div>
    <div class="col-4">
      <q-select v-model="value" outlined dense options-dense :readonly="!tnIsEditable" :options="choiceOptions" />
    </div>
    <q-space />
    <CodeBadge label="choice" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { QTreeNode } from 'quasar';
import { useTreeNode } from './useTreeNode';
import type { ConfigContext } from 'src/ts/treenodes/ConfigStateTypes';
import { UNSET_DROPDOWN } from 'src/ts/TreeNodeUtils';
import TreeNodeLabel from './TreeNodeLabel.vue';
import CodeBadge from 'components/helpers/CodeBadge.vue';

const props = defineProps<{ context: ConfigContext; node: QTreeNode }>();

const { value, tnIsEditable, tnIsOptional, tnSchema } = useTreeNode({
  context: props.context,
  node: props.node,
});

const choiceOptions = computed(() => {
  const result: string[] = [];

  if (tnIsOptional.value) {
    result.push(UNSET_DROPDOWN);
  }

  const caseArr = tnSchema.value?.cases ?? [];
  for (const nodeCase of caseArr) {
    result.push(nodeCase?.name);
  }

  return result.filter((item): item is string => typeof item === 'string');
});
</script>
