<template>
  <div>
    <TooltipChild tooltip="create list entry">
      <q-btn dense size="xs" icon="playlist_add" @click="isDialogOn = true" />
    </TooltipChild>

    <q-dialog v-model="isDialogOn">
      <q-card>
        <q-card-section class="row items-baseline text-h6 q-gutter-x-sm">
          <div class="row">Create new entry of "{{ tnLabel }}":</div>
          <div class="row">
            <CodeBadge floating label="keypath" :tooltip="`${tnKeypath}{}`" />
          </div>
        </q-card-section>
        <q-separator />
        <q-card-section v-if="listSchema">
          <div v-for="(schema, index) in schemaKeys" :key="index" class="row items-center q-mb-sm">
            <div class="column col-3">
              {{ schema['name'] }}
            </div>
            <div class="column" v-if="keysArray">
              <component :is="paramByType(schema)" v-model="keysArray[index]" :schema="schema" />
            </div>
          </div>
        </q-card-section>

        <q-separator />

        <q-card-actions align="right">
          <q-btn v-close-popup label="Cancel" />
          <q-btn label="Create" color="primary" @click="doCreate()" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useErrorsStore } from 'src/stores/errors';
import { useServerStore } from 'src/stores/server';
import { nodeKind } from 'src/ts/TreeNodeUtils';
import { addListEntry } from 'src/ts/treenodes/ConfigChanges';
import type { ConfigContext } from 'src/ts/treenodes/ConfigStateTypes';
import * as te from 'src/ts/TypeExtractor';
import { useTreeNode } from './useTreeNode';
import CodeBadge from 'components/helpers/CodeBadge.vue';
import TooltipChild from 'components/helpers/TooltipChild.vue';
import ParamBoolean from './params/ParamBoolean.vue';
import ParamEnum from './params/ParamEnum.vue';
import ParamString from './params/ParamString.vue';
import type { TreeNode } from 'src/ts/TreeNodeTypes';

const props = defineProps<{ context: ConfigContext; node: TreeNode }>();

const isDialogOn = ref(false);
const listSchema = ref<Record<string, any> | null>(null);
const keysArray = ref<string[] | null>(null);

const schemaKeys = () => {
  const result: any[] = [];
  const children = listSchema.value?.children || [];
  for (const child of children) {
    if (nodeKind(child) === 'key') result.push(child);
  }
  return result;
};

const errorsStore = useErrorsStore();

const { tnLabel, tnKeypath, tnModuleTypes } = useTreeNode({ context: props.context, node: props.node });

async function getListSchema() {
  const serverStore = useServerStore();
  const tasks = serverStore.tasks;
  if (!tasks) return;

  try {
    const schemaData = await tasks.schema.getLevelSchema(tnKeypath.value);
    listSchema.value = schemaData;
    const len = schemaKeys().length;
    keysArray.value = Array(len).fill('');
  } catch {
    errorsStore.addActive('did not load list schema!');
  }
}

onMounted(() => {
  void getListSchema();
});

async function doCreate() {
  const vmKeys = keysArray.value || [];
  const keysString = vmKeys.map((x) => `"${x}"`).join(' ');
  const createKeypath = `${tnKeypath.value}{${keysString}}`;
  const serverStore = useServerStore();
  const tasks = serverStore.tasks;
  if (!tasks) return;

  try {
    const doesExist = await tasks.data.existsPath(createKeypath);
    if (doesExist) {
      errorsStore.addActive('Such entry already exists!');
      return;
    }

    await tasks.data.createPath(createKeypath);
    isDialogOn.value = false;
    addListEntry(props.context, props.node, vmKeys);
  } catch {
    errorsStore.addActive('did not create list entry!');
  }
}

const paramByType = (leafSchema: any) => {
  // tree node component to be used for specific internal type
  const componentMap = {
    [te.T_BOOL]: ParamBoolean,
    [te.T_ENUM]: ParamEnum,
    [te.T_NUMBER]: ParamString,
    [te.T_STRING]: ParamString,
  };
  const mappingParams = { leafSchema, moduleTypesSchema: tnModuleTypes.value, componentMap };
  const pComponent = te.getComponentByType(mappingParams) || ParamString;
  return pComponent;
};
</script>
