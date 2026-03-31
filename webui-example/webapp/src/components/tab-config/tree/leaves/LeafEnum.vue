<template>
  <q-select dense options-dense outlined :options="enumOptions" :readonly="!tnIsEditable" v-model="value" />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useTreeNode } from '../useTreeNode';
import type { ConfigContext } from 'src/ts/treenodes/ConfigStateTypes';
import { enumOptionsFromSchema } from 'src/ts/TypeExtractor';
import type { TreeNode } from 'src/ts/TreeNodeTypes';

const props = defineProps<{ context?: ConfigContext; node: TreeNode }>();

const { value, tnIsEditable, tnSchema, tnModuleTypes } = useTreeNode({
  context: props.context,
  node: props.node,
} as any);

const enumOptions = computed(() => enumOptionsFromSchema(tnSchema.value, tnModuleTypes.value));
</script>
