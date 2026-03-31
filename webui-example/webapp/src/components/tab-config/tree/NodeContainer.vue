<template>
  <div class="row col-12 items-baseline">
    <div class="column col-4">
      <tree-node-label :context="context" :node="node" />
    </div>

    <div v-if="isPresenceTrue">
      <q-toggle
        v-model="value"
        dense
        :disable="!tnIsEditable"
        checked-icon="check"
        unchecked-icon="clear"
        :label="presenceLabel"
      />
    </div>

    <q-space />

    <CodeBadge v-if="isPresenceTrue" label="!" tooltip="presence: true;" />

    <CodeBadge label="container" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { QTreeNode } from 'quasar';
import { useTreeNode } from './useTreeNode';
import { updateNode } from 'src/ts/treenodes/ConfigChanges';
import { getState } from 'src/ts/treenodes/ConfigCommons';
import type { ConfigContext } from 'src/ts/treenodes/ConfigStateTypes';
import { nodeSchema } from 'src/ts/TreeNodeUtils';
import TreeNodeLabel from './TreeNodeLabel.vue';
import CodeBadge from 'components/helpers/CodeBadge.vue';

const props = defineProps<{ context: ConfigContext; node: QTreeNode }>();

const { tnIsEditable } = useTreeNode({
  context: props.context,
  node: props.node,
});

const value = computed({
  get: () => getState(props.context.state, props.node),
  set: (v: any) => updateNode(props.context, props.node, v),
});

const tnSchema = computed(() => nodeSchema(props.node));
const isPresenceTrue = computed(() => tnSchema.value['presence'] === true);
const presenceLabel = computed(() => (value.value ? 'present' : 'does not exist'));
</script>
