<template>
  <div class="row col-12 items-center" @click.stop @keypress.enter.space.stop>
    <div class="row col-4">
      <tree-node-label :context="context" :node="node" />
      <CodeBadge v-if="leafIsUnionTyped" label="U" tooltip="type union" />
    </div>

    <div class="column col-4">
      <!-- leaf value customized by base type -->
      <component :is="componentByType" v-model="value" :readonly="tnIsReadOnly" :context="context" :node="node">
        <template v-slot:delete>
          <TooltipChild v-if="leafIsDeletable" tooltip="delete">
            <q-icon name="delete_forever" class="cursor-pointer" @click="doDeleteLeaf" />
          </TooltipChild>
        </template>
      </component>
    </div>

    <q-space />

    <!-- other leaf related info / controls -->
    <div class="q-ml-sm">
      <CodeBadge v-if="tnHasDefault && !tnIsDefault" label="D" :tooltip="'default: ' + tnDefaultValue" />
      <CodeBadge v-if="tnIsOptional" label="?" tooltip="optional leaf" />
      <CodeBadge v-if="tnIsTypeEmpty" label="E" tooltip="type empty leaf" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { QTreeNode } from 'quasar';
import { updateNode } from 'src/ts/treenodes/ConfigChanges';
import { getState } from 'src/ts/treenodes/ConfigCommons';
import type { ConfigContext } from 'src/ts/treenodes/ConfigStateTypes';
import { nodeSchema } from 'src/ts/TreeNodeUtils';
import * as te from 'src/ts/TypeExtractor';
import { useTreeNode } from './useTreeNode';
import TreeNodeLabel from './TreeNodeLabel.vue';
import CodeBadge from 'components/helpers/CodeBadge.vue';
import TooltipChild from 'components/helpers/TooltipChild.vue';
import LeafBoolean from './leaves/LeafBoolean.vue';
import LeafEnum from './leaves/LeafEnum.vue';
import LeafString from './leaves/LeafString.vue';

const props = defineProps<{ context: ConfigContext; node: QTreeNode }>();

const { tnHasDefault, tnIsDefault, tnIsOptional, tnModuleTypes, tnIsReadOnly } = useTreeNode({
  context: props.context,
  node: props.node,
});

const value = computed({
  get: () => getState(props.context.state, props.node),
  set: (v: any) => updateNode(props.context, props.node, v),
});

const tnSchema = computed(() => nodeSchema(props.node));
const tnIsTypeEmpty = computed(() => {
  const schemaType = tnSchema.value['type'];
  if (!schemaType) return false;
  const isPrimitive = schemaType['primitive'] === true || false;
  const isEmpty = schemaType['name'] === 'empty';
  return isPrimitive && isEmpty;
});

const tnDefaultValue = computed(() => tnSchema.value['default']);

const leafIsDeletable = computed(
  () => !tnIsReadOnly.value && !tnIsTypeEmpty.value && value.value !== null && value.value !== tnDefaultValue.value,
);

function doDeleteLeaf() {
  value.value = tnDefaultValue.value;
}

const componentByType = computed(() => {
  // tree node component to be used for specific internal type
  const componentMap = {
    [te.T_BOOL]: LeafBoolean,
    [te.T_ENUM]: LeafEnum,
    [te.T_NUMBER]: LeafString,
    [te.T_STRING]: LeafString,
  };
  const leafSchema = tnSchema.value;
  const moduleTypesSchema = tnModuleTypes.value;
  const mappingParams = { leafSchema, moduleTypesSchema, componentMap };
  const leafComponent = te.getComponentByType(mappingParams) || LeafString;
  return leafComponent;
});

const leafIsUnionTyped = computed(() => te.isTypeUnion(tnSchema.value, tnModuleTypes.value));
</script>
