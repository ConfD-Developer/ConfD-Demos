<template>
  <div>
    <TooltipChild tooltip="delete whole list">
      <q-btn dense size="xs" icon="delete_forever" @click="isDialogOn = true" />
    </TooltipChild>

    <q-dialog v-model="isDialogOn">
      <q-card>
        <q-card-section class="row items-center">
          <div class="column">
            <span>Delete all list entries of the list:</span>
            <div class="text-h6">
              {{ tnKeypath }}
            </div>
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn v-close-popup label="Cancel" />
          <q-btn v-close-popup label="Delete ALL" color="primary" @click="doDeleteList()" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useTreeNode } from './useTreeNode';
import { deleteList } from 'src/ts/treenodes/ConfigChanges';
import type { ConfigContext } from 'src/ts/treenodes/ConfigStateTypes';
import TooltipChild from 'components/helpers/TooltipChild.vue';
import type { TreeNode } from 'src/ts/TreeNodeTypes';

const props = defineProps<{ context: ConfigContext; node: TreeNode }>();

const { tnKeypath } = useTreeNode({ context: props.context, node: props.node });

const isDialogOn = ref(false);

function doDeleteList() {
  deleteList(props.context, props.node);
}
</script>
