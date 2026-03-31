<template>
  <div>
    <TreeHeader
      v-model="filter"
      filter-label="Filter config node names"
      :disable="false"
      warning="filtering on previously unfolded tree nodes only!"
      @expandAll="treeRef?.expandAll()"
      @collapseAll="treeRef?.collapseAll()"
    />

    <q-tree
      :ref="treeName"
      :node-key="columnNameKey()"
      :label-key="columnNameLabel()"
      v-model:selected="selectedNode"
      v-model:expanded="expandedNodes"
      :nodes="treeNodes"
      :filter="filter"
      @lazy-load="onLazyLoad"
    >
      <template v-slot:header-root> module root nodes: </template>

      <template v-if="hasContext" v-slot:header-container="{ node }: { node: QTreeNode }">
        <node-container v-bind="nodePropsOf(node)" />
      </template>

      <template v-if="hasContext" v-slot:header-list="{ node }: { node: QTreeNode }">
        <node-list v-bind="nodePropsOf(node)" />
      </template>
      <template v-if="hasContext" v-slot:body-list="{ node }: { node: QTreeNode }">
        <node-list-body v-bind="nodePropsOf(node)" />
      </template>

      <template v-if="hasContext" v-slot:header-list-entry="{ node }: { node: QTreeNode }">
        <node-list-entry v-bind="nodePropsOf(node)" />
      </template>

      <template v-if="hasContext" v-slot:header-leaf="{ node }: { node: QTreeNode }">
        <node-leaf v-bind="nodePropsOf(node)" />
      </template>

      <template v-slot:header-action>
        <div class="bg-yellow">TODO - actions not implemented</div>
      </template>

      <template v-if="hasContext" v-slot:header-leaf-list="{ node }: { node: QTreeNode }">
        <node-leaf-list v-bind="nodePropsOf(node)" />
      </template>
      <template v-if="hasContext" v-slot:body-leaf-list="{ node }: { node: QTreeNode }">
        <node-leaf-list-body v-bind="nodePropsOf(node)" />
      </template>

      <template v-if="hasContext" v-slot:header-key="{ node }: { node: QTreeNode }">
        <node-key v-bind="nodePropsOf(node)" />
      </template>

      <template v-if="hasContext" v-slot:header-choice="{ node }: { node: QTreeNode }">
        <node-choice v-bind="nodePropsOf(node)" />
      </template>
    </q-tree>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, useTemplateRef } from 'vue';
import { QTree } from 'quasar';
import type { QTreeNode } from 'quasar';
import { useServerStore } from 'src/stores/server';
import { bindData } from 'src/ts/treenodes/ConfigBindings';
import { getLazyNodes } from 'src/ts/treenodes/ConfigLazyLoad';
import type { ConfigContext, ConfigState } from 'src/ts/treenodes/ConfigStateTypes';
import { generateToplevelNode } from 'src/ts/treenodes/GeneratorConfig';
import { columnNameKey, columnNameLabel } from 'src/ts/TreeNodeUtils';
import NodeChoice from './tree/NodeChoice.vue';
import NodeContainer from './tree/NodeContainer.vue';
import NodeKey from './tree/NodeKey.vue';
import NodeLeaf from './tree/NodeLeaf.vue';
import NodeLeafList from './tree/NodeLeafList.vue';
import NodeLeafListBody from './tree/NodeLeafListBody.vue';
import NodeList from './tree/NodeList.vue';
import NodeListBody from './tree/NodeListBody.vue';
import NodeListEntry from './tree/NodeListEntry.vue';
import TreeHeader from 'components/TreeHeader.vue';

const props = defineProps<{ moduleData: any }>();

const treeName = 'tree-configs';
const treeRef = useTemplateRef<QTree>(treeName);

const selectedNode = ref<any>(null);
const expandedNodes = ref<Array<any>>([]);
const filter = ref('');
const configStateData = ref<ConfigState>({});
const treeNodes = ref<QTreeNode[]>([]);
const serverStore = useServerStore();

const context = computed<ConfigContext | null>(() => {
  if (!treeRef.value) return null;
  return {
    state: configStateData.value,
    tasker: serverStore.tasks,
    tree: treeRef.value,
  };
});

const hasContext = computed(() => context.value !== null);

watch(
  () => props.moduleData,
  () => {
    reinitTree();
  },
);

onMounted(() => reinitTree());

function nodePropsOf(node: QTreeNode) {
  return { context: context.value as ConfigContext, node };
}

function reinitTree() {
  configStateData.value = {};
  treeNodes.value = rootNodes();
  if (treeRef.value) {
    // treeRef.value.lazy = {} TODO
    if ('children' in treeRef.value) {
      delete treeRef.value['children'];
    }
  }
}

function rootNodes() {
  const moduleName = props.moduleData['name'];
  const schema = props.moduleData['schema'];
  const rootNode = generateToplevelNode(moduleName, schema);
  if (context.value) {
    bindData(context.value, rootNode['children'] ?? []);
  }
  return [rootNode];
}

function onLazyLoad({ node, done, fail }) {
  void (async () => {
    try {
      if (!context.value) {
        done([]);
        return;
      }
      const nodes = await getLazyNodes(context.value, node);
      bindData(context.value, nodes);
      done(nodes);
    } catch (error: any) {
      fail(error);
    }
  })();
}
</script>
