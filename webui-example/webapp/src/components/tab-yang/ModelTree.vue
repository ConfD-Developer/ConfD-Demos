<!-- Quasar QTree of YANG schema module nodes -->
<template>
  <div>
    <!-- header with some controls -->
    <tree-header
      v-model="filter"
      filter-label="Filter node name"
      :disable="noNodesPresent"
      @expandAll="treeRef?.expandAll()"
      @collapseAll="treeRef?.collapseAll()"
    />

    <q-tree
      :ref="treeName"
      :node-key="columnNameKey()"
      :label-key="columnNameLabel()"
      v-model:selected="selectedNode"
      :nodes="modelTreeNodes"
      :filter="filter"
    >
      <!-- formatting for root node of tree -->
      <template v-slot:header-root="{ node }">
        <div class="row items-baseline">
          <div>module</div>
          <div class="text-weight-bold text-primary q-ml-xs">"{{ nodeLabel(node) }}"</div>
          <div v-if="noNodesPresent">has no configuration / status nodes</div>
        </div>
      </template>

      <!-- formatting all other rows -->
      <template v-slot:default-header="{ node }">
        <div class="row col-12">
          <div class="row col-4 items-center">
            <!-- flag - choice -->
            <CodeBadge v-if="nodeKind(node) === 'choice'" label="choice" tooltip="'choice' YANG statement" />

            <!-- flag - case -->
            <CodeBadge v-if="nodeKind(node) === 'case'" label="case" tooltip="'case' YANG statement" />

            <!-- YANG node name -->
            <div :class="configColor(node)">
              {{ nodeLabel(node) }}
            </div>

            <!-- list keys, if applicable -->
            <div v-if="nodeKind(node) === 'list'" :class="'q-ml-xs ' + configColor(node)">
              {{ schemaOf(node)?.['key'] }}
            </div>

            <!-- key of the list -->
            <CodeBadge v-if="nodeKind(node) === 'key'" label="K" tooltip="list key" />
            <!-- "presence true" -->
            <CodeBadge v-if="schemaOf(node)?.['presence'] === true" label="!" tooltip="presence: true;" />
            <!-- "optional" -->
            <CodeBadge v-if="nodeOptional(node)" label="?" tooltip="mandatory: false;" />
          </div>

          <div class="row col-3 items-center">
            <!-- data type of leaf -->
            <div v-if="schemaOf(node)?.['type']" class="text-italic">
              {{ schemaOf(node)?.type?.name }}
              <q-tooltip>
                <pre>type: {{ subNodeToString(node, 'type') }}</pre>
              </q-tooltip>
            </div>
            <!-- default value -->
            <CodeBadge
              v-if="schemaOf(node)?.default"
              label="D"
              :tooltip="'default: ' + subNodeToString(node, 'default')"
            />
          </div>

          <div class="row col-1 items-center">
            <!-- access rights -->
            <CodeBadge
              v-if="schemaOf(node)?.['access']"
              :label="stringifyAccess(schemaOf(node)?.access)"
              :tooltip="'access: ' + subNodeToString(node, 'access')"
            />
          </div>

          <q-space />

          <!-- node's schema source -->
          <CodeBadge label="json" :tooltip="JSON.stringify(schemaOf(node) ?? {}, null, 2) || ''" />
        </div>
      </template>
    </q-tree>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, useTemplateRef } from 'vue';
import { QTree } from 'quasar';
import { generateModelNodes } from 'src/ts/treenodes/GeneratorModel';
import type { TreeNode } from 'src/ts/TreeNodeTypes';
import { nodeSchema, nodeKind, nodeLabel, columnNameKey, columnNameLabel } from 'src/ts/TreeNodeUtils';
import type { YangModuleSchema, YangSchemaNode } from 'src/ts/YangSchemaTypes';
import TreeHeader from '../TreeHeader.vue';
import CodeBadge from 'components/helpers/CodeBadge.vue';

const props = defineProps<{ moduleName: string; schema: YangModuleSchema }>();

const treeName = 'tree-module';
const treeRef = useTemplateRef<QTree>(treeName);

const selectedNode = ref(null);
const filter = ref('');

const modelTreeNodes = computed(() => generateModelNodes(props.moduleName, props.schema.data));

const noNodesPresent = computed(() => {
  const nodes = modelTreeNodes.value;
  const children = nodes?.[0]?.children;
  return !(children && children.length > 0);
});

function schemaOf(node: TreeNode): YangSchemaNode {
  return nodeSchema(node);
}

function subNodeToString(node: TreeNode, prop: string) {
  return JSON.stringify(schemaOf(node)[prop], null, 2);
}

function nodeOptional(node: TreeNode) {
  const schema = schemaOf(node);
  const isConfigTrue = !isConfigFalse(node);
  const isMandatory = schema['mandatory'] !== true;
  return isConfigTrue && !isMandatory;
}

function isConfigFalse(node: TreeNode) {
  const schema = schemaOf(node);
  return 'config' in schema ? schema['config'] === false : false;
}

function configColor(node: TreeNode) {
  return isConfigFalse(node) ? 'text-secondary' : 'text-black';
}

function stringifyAccess(accessNode: any) {
  const accesRights = ['create', 'read', 'update', 'delete', 'execute'];
  let crudeString = '';
  accesRights
    .filter((accRight) => accessNode[accRight] === true)
    .forEach((prop) => {
      crudeString += prop[0];
    });
  return crudeString.toUpperCase();
}
</script>
