<template>
  <div class="row col-12 items-baseline">
    <div class="column col-4">
      <tree-node-label :context="context" :node="node" />
    </div>

    <div class="column col-4">
      <q-input v-model="tnValue" dense outlined readonly @click.stop />
    </div>

    <q-space />

    <CodeBadge label="key" />
  </div>
</template>

<script setup lang="ts">
import type { QTreeNode } from 'quasar';
import { useTreeNode } from './useTreeNode';
import type { ConfigContext } from 'src/ts/treenodes/ConfigStateTypes';
import TreeNodeLabel from './TreeNodeLabel.vue';
import CodeBadge from 'components/helpers/CodeBadge.vue';

const props = defineProps<{ context: ConfigContext; node: QTreeNode }>();

const { tnValue } = useTreeNode({
  context: props.context,
  node: props.node,
});
</script>
