<template>
  <div>
    <q-btn dense flat icon="help_outline" @click="helpDialogVisible = true" />
    <q-dialog v-model="helpDialogVisible">
      <q-card>
        <q-card-section>
          <div class="row nowrap items-center">
            <div class="text-h6">
              Type info for "<span class="text-bold">{{ tnLabel }}</span
              >"
            </div>
            <q-space />
            <div>
              <CodeBadge label="keypath" :tooltip="tnKeypath" />
            </div>
          </div>
          <q-separator />
        </q-card-section>
        <q-card-section>
          <div class="text-h6">Leaf type</div>
          <CodeBlock :text="leafTypeNode" />
        </q-card-section>
        <q-card-section v-if="leafTypeChain">
          <div class="text-h6">Leaf type chain</div>
          <div v-for="(subType, index) in leafTypeChain" :key="index">
            <CodeBlock :text="subType" />
            <q-separator />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useTreeNode } from '../useTreeNode';
import type { ConfigContext } from 'src/ts/treenodes/ConfigStateTypes';
import CodeBadge from 'components/helpers/CodeBadge.vue';
import CodeBlock from 'components/helpers/CodeBlock.vue';
import type { TreeNode } from 'src/ts/TreeNodeTypes';

const props = defineProps<{ context?: ConfigContext; node: TreeNode }>();

const { tnKeypath, tnLabel, tnSchema, tnModuleTypes } = useTreeNode({
  context: props.context,
  node: props.node,
} as any);

const helpDialogVisible = ref(false);

const leafTypeNode = computed(() => tnSchema.value && tnSchema.value['type']);

const leafTypeChain = computed(() => {
  const node = leafTypeNode.value;
  if (!node) return null;
  const { namespace, name } = node;
  const chainTypeName = `${namespace}:${name}`;
  return tnModuleTypes.value && tnModuleTypes.value[chainTypeName];
});
</script>
