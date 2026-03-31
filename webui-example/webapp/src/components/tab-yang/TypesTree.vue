<!-- Quasar QTree of YANG schema type definitions. -->
<template>
  <div>
    <!-- header with some controls -->
    <tree-header
      v-model="filter"
      filter-label="Filter type name"
      :disable="noNodesPresent"
      @expandAll="treeRef?.expandAll()"
      @collapseAll="treeRef?.collapseAll()"
    />

    <q-tree
      :ref="treeName"
      :node-key="treePropKey"
      :label-key="treePropLabel"
      v-model:selected="selectedNode"
      :nodes="typeTreeNodes"
      :filter="filter"
    >
      <!-- formatting for root node of tree -->
      <template v-slot:header-root="{ node }">
        <div class="row col-12 items-baseline q-gutter-x-xs">
          <div>types of module</div>
          <div class="text-weight-bold text-primary">"{{ nodeLabel(node) }}"</div>
          <div v-if="noNodesPresent">has none defined</div>
        </div>
      </template>

      <!-- formatting for "namespace" nodes -->
      <template v-slot:header-namespace="{ node }">
        <div class="row col-12 items-baseline q-gutter-x-xs">
          <div>from namespace</div>
          <div class="text-weight-bold">"{{ node.name }}"</div>
        </div>
      </template>

      <!-- formatting for "type" nodes -->
      <template v-slot:header-type="{ node }">
        <type-details :node="node" />
      </template>
    </q-tree>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, useTemplateRef } from 'vue';
import { QTree } from 'quasar';
import { resolveNested } from 'src/ts/CommonUtils';
import { generateTypeNodes } from 'src/ts/treenodes/GeneratorTypes';
import { nodeLabel, columnNameKey, columnNameLabel } from 'src/ts/TreeNodeUtils';
import TreeHeader from '../TreeHeader.vue';
import TypeDetails from './TypeDetails.vue';

const props = defineProps<{ moduleName: string; schema: any }>();

const treeName = 'tree-types';
const treeRef = useTemplateRef<QTree>(treeName);

const selectedNode = ref(null);
const filter = ref('');

const typeTreeNodes = computed(() => {
  const moduleTypes = resolveNested(props.schema, ['meta', 'types']);
  return generateTypeNodes(props.moduleName, moduleTypes);
});

const noNodesPresent = computed(() => {
  const nodes = typeTreeNodes.value;
  return !(nodes && nodes.length > 0 && nodes[0]?.children && nodes[0].children.length > 0);
});

const treePropKey = computed(() => columnNameKey());
const treePropLabel = computed(() => columnNameLabel());
</script>
