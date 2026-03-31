<template>
  <div>
    <TooltipChild tooltip="add value">
      <q-btn dense icon="playlist_add" size="xs" @click="isDialogOn = true" />
    </TooltipChild>

    <q-dialog v-model="isDialogOn">
      <q-card>
        <q-card-section class="row items-baseline text-h6 q-gutter-x-sm">
          <div class="row">Add value to "{{ tnLabel }}":</div>
          <div class="row">
            <CodeBadge floating label="keypath" :tooltip="tnKeypath" />
          </div>
        </q-card-section>
        <q-separator />
        <q-card-section>
          <div class="row items-center q-mb-sm">
            <div class="column col-3">value:</div>
            <div class="column">
              <q-input v-model="valueToAdd" dense outlined hide-bottom-space />
            </div>
          </div>
        </q-card-section>

        <q-separator />

        <q-card-actions align="right">
          <q-btn v-close-popup label="Cancel" />
          <q-btn label="Add" color="primary" @click="doAddValue()" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, getCurrentInstance } from 'vue';
import { storeToRefs } from 'pinia';
import { useTreeNode } from './useTreeNode';
import { useServerStore } from 'src/stores/server';
import { addLeafListEntry } from 'src/ts/treenodes/ConfigChanges';
import type { ConfigContext } from 'src/ts/treenodes/ConfigStateTypes';
import CodeBadge from 'components/helpers/CodeBadge.vue';
import TooltipChild from 'components/helpers/TooltipChild.vue';
import type { TreeNode } from 'src/ts/TreeNodeTypes';

const props = defineProps<{ context?: ConfigContext; node: TreeNode; currentValues?: any[] }>();

const { tnKeypath, tnLabel } = useTreeNode({ context: props.context, node: props.node } as any);
const { tasks } = storeToRefs(useServerStore());

const isDialogOn = ref(false);
const valueToAdd = ref('');

function setError(err: any) {
  const errors = (getCurrentInstance() as any)?.appContext.config.globalProperties.$errors;
  errors?.addActive(err);
}

async function doAddValue() {
  const createKeypath = `${tnKeypath.value}{"${valueToAdd.value}"}`;

  const doesExist = await tasks.value?.data.existsPath(createKeypath);

  if (doesExist) {
    setError('Value already set!');
  } else {
    try {
      await tasks.value?.data.createPath(createKeypath);
      isDialogOn.value = false;
      addLeafListEntry((props as any).context, props.node, valueToAdd.value);
      valueToAdd.value = '';
    } catch (error: any) {
      setError(error);
    }
  }
}
</script>
