<template>
  <div class="row col-12 items-baseline">
    <div class="row col-4">
      <tree-node-label :context="context" :node="node" />
    </div>

    <div class="q-pl-sm">
      <TooltipChild :tooltip="'delete ' + tnLabel">
        <q-btn
          v-if="tnIsEditable"
          dense
          size="xs"
          icon="delete_forever"
          class="cursor-pointer"
          @click="doDeleteEntry()"
        />
      </TooltipChild>
    </div>

    <q-space />

    <CodeBadge label="list-entry" />
  </div>
</template>

<script setup lang="ts">
import type { QTreeNode } from 'quasar';
import { useTreeNode } from './useTreeNode';
import { deleteListEntry } from 'src/ts/treenodes/ConfigChanges';
import type { ConfigContext } from 'src/ts/treenodes/ConfigStateTypes';
import TreeNodeLabel from './TreeNodeLabel.vue';
import CodeBadge from 'components/helpers/CodeBadge.vue';
import TooltipChild from 'components/helpers/TooltipChild.vue';

const props = defineProps<{ context: ConfigContext; node: QTreeNode }>();

const { tnLabel, tnIsEditable } = useTreeNode({
  context: props.context,
  node: props.node,
});

function doDeleteEntry() {
  deleteListEntry(props.context, props.node);
}
</script>
