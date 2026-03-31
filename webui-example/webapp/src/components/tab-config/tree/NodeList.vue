<template>
  <div class="row col-12 items-center">
    <div class="row col-4">
      <tree-node-label :context="context" :node="node" />
      ~ {{ listTotal }} {{ entryString }}
    </div>

    <div class="row col-4 q-gutter-x-sm">
      <div v-if="isListIterable">
        <TooltipChild tooltip="show first">
          <q-btn dense size="xs" icon="first_page" @click="doGetFirst" />
        </TooltipChild>
      </div>
      <div v-if="isListIterable">
        <TooltipChild tooltip="show next batch">
          <q-btn dense size="xs" icon="navigate_next" @click="doGetNext()" />
        </TooltipChild>
      </div>
      <div v-if="tnIsEditable">
        <node-list-create-dialog :context="context" :node="node" />
      </div>
      <div v-if="tnIsEditable">
        <node-list-delete-dialog v-show="listTotal > 0" :context="context" :node="node" />
      </div>
    </div>

    <q-space />

    <CodeBadge label="list" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { QTreeNode } from 'quasar';
import { useTransactionStore } from 'src/stores/transaction';
import { getNextListEntries } from 'src/ts/treenodes/ConfigChanges';
import { updateNode } from 'src/ts/treenodes/ConfigChanges';
import { getState } from 'src/ts/treenodes/ConfigCommons';
import type { ConfigContext, ListMeta } from 'src/ts/treenodes/ConfigStateTypes';
import NodeListCreateDialog from './NodeListCreateDialog.vue';
import NodeListDeleteDialog from './NodeListDeleteDialog.vue';
import TreeNodeLabel from './TreeNodeLabel.vue';
import CodeBadge from 'components/helpers/CodeBadge.vue';
import TooltipChild from 'components/helpers/TooltipChild.vue';

const props = defineProps<{ context: ConfigContext; node: QTreeNode }>();

const transactionStore = useTransactionStore();

const value = computed({
  get: () => getState(props.context.state, props.node),
  set: (newVal: any) => updateNode(props.context, props.node, newVal),
});

const listData = computed(() => value.value as ListMeta | undefined);
const listTotal = computed(() => listData.value?.total ?? 0);
const isListIterable = computed(() => listTotal.value > 0 && (listData.value?.position ?? -1) >= 0);
const entryString = computed(() => (listTotal.value === 1 ? 'entry' : 'entries'));

const tnIsEditable = computed(
  () => transactionStore.transHandle !== -1 && transactionStore.isWriteTrans && props.node.schema.config == true,
);

function doGetNext() {
  void getNextListEntries(props.context, props.node, false);
}
function doGetFirst() {
  void getNextListEntries(props.context, props.node, true);
}
</script>
