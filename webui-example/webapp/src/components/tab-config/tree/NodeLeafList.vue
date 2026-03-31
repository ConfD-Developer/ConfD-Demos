<template>
  <div class="row col-12 items-baseline">
    <div class="column col-4">
      <tree-node-label :context="context" :node="node" />
    </div>
    <div v-if="tnIsEditable" class="row q-gutter-x-sm">
      <div>
        <node-leaf-list-create-dialog :context="context" :node="node" :current-values="value" />
      </div>
      <div v-if="value?.length > 0">
        <TooltipChild tooltip="delete all">
          <q-btn dense icon="delete_forever" size="sm" @click="doDeleteAll()" />
        </TooltipChild>
      </div>
    </div>
    <q-space />
    <CodeBadge label="leaf-list" />
  </div>
</template>

<script setup lang="ts">
import type { QTreeNode } from 'quasar';
import { useTreeNode } from './useTreeNode';
import type { ConfigContext } from 'src/ts/treenodes/ConfigStateTypes';
import NodeLeafListCreateDialog from './NodeLeafListCreateDialog.vue';
import TreeNodeLabel from './TreeNodeLabel.vue';
import CodeBadge from 'components/helpers/CodeBadge.vue';
import TooltipChild from 'components/helpers/TooltipChild.vue';

const props = defineProps<{ context: ConfigContext; node: QTreeNode }>();

const { value, tnIsEditable } = useTreeNode({
  context: props.context,
  node: props.node,
});

function doDeleteAll() {
  value.value = null;
}
</script>
