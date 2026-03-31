<template>
  <div v-if="!activeNamespace" class="q-mt-lg text-center text-h6">
    <div v-if="!connected">Connect to a device.</div>
    <div v-if="!hasTrans">Open a read/write transaction to access device models.</div>
    Pick some of the device models in menu on the left.
  </div>
  <div v-else class="q-gutter-y-xs">
    <div class="text-h6 q-mb-md">YANG model details</div>

    <div class="row q-gutter-x-md">
      <div class="column col-1 items-end">name:</div>
      <div class="text-bold">
        <CodeBlock :text="activeModel.name" :greyed="false" />
      </div>
    </div>

    <div class="row q-gutter-x-md">
      <div class="column col-1 items-end">prefix:</div>
      <div>
        <CodeBlock :text="activeModel.prefix" :greyed="false" />
      </div>
    </div>

    <div class="row q-gutter-x-md">
      <div class="column col-1 items-end">namespace:</div>
      <div>
        <CodeBlock :text="activeNamespace" :greyed="false" />
      </div>
    </div>

    <q-tabs
      v-model="activeTab"
      dense
      class="q-mt-md text-grey"
      active-color="primary"
      indicator-color="primary"
      align="justify"
      narrow-indicator
    >
      <q-tab name="tree" label="model tree" />
      <q-tab name="raw" label="raw schema" />
    </q-tabs>

    <q-separator class="q-mb-lg" />

    <q-tab-panels v-model="activeTab" animated>
      <q-tab-panel name="tree">
        <types-tree :module-name="activeModel.name" :schema="activeSchema" />
        <q-separator class="q-my-md" />
        <model-tree :module-name="activeModel.name" :schema="activeSchema" />
      </q-tab-panel>
      <q-tab-panel name="raw">
        <CodeBlock :text="activeSchema" />
      </q-tab-panel>
    </q-tab-panels>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useModelsStore } from 'src/stores/models';
import { useServerStore } from 'src/stores/server';
import { useTransactionStore } from 'src/stores/transaction';
import ModelTree from './ModelTree.vue';
import TypesTree from './TypesTree.vue';
import CodeBlock from 'components/helpers/CodeBlock.vue';

const modelsStore = useModelsStore();
const txStore = useTransactionStore();
const serverStore = useServerStore();

const { activeNamespace, loadedModels } = storeToRefs(modelsStore);
const activeModel = computed(() => (activeNamespace.value ? loadedModels.value[activeNamespace.value] : {}));
const activeSchema = computed(() => activeModel.value?.schema);

const activeTab = ref('tree');
const { hasTrans } = storeToRefs(txStore);
const { connected } = storeToRefs(serverStore);
</script>
