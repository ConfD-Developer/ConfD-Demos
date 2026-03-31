<template>
  <div class="col-12 items-baseline q-gutter-x-xs">
    <!-- <div class="row col-12 items-baseline q-gutter-x-xs">
      <div>type</div>
      <div>"{{ node['name'] }}"</div>
      <q-space />
    </div> -->
    <q-expansion-item v-model="expState" dense icon="view_headline" :label="expansionLabel">
      <CodeBlock :text="typeSchema" :greyed="true" />
    </q-expansion-item>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { TreeNode } from 'src/ts/TreeNodeTypes';
import { nodeLabel, nodeSchema } from 'src/ts/TreeNodeUtils';
import CodeBlock from 'components/helpers/CodeBlock.vue';

const props = defineProps<{ node: TreeNode }>();

const expState = ref(false);

const typeSchema = computed(() => nodeSchema(props.node));

const expansionLabel = computed(() => {
  const typeName = nodeLabel(props.node);
  const stateStr = expState.value ? 'collapse' : 'expand';
  return `type-chain of "${typeName}" (click to ${stateStr})`;
});
</script>
