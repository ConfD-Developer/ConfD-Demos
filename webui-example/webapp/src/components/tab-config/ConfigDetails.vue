<template>
  <div v-if="!activeNamespace" class="q-mt-lg text-center text-h6">
    <div v-if="!connected">Connect to a device.</div>
    <div v-if="!hasTrans">Open a read/write transaction to access device configuration.</div>
    Pick some of the device configurations in menu on the left.
  </div>
  <div v-else class="q-pa-sm q-gutter-y-md">
    <div class="row items-baseline q-gutter-x-xs">
      <div class="text-h6">Configuration of module</div>
      <div class="text-h5">"{{ moduleData.name }}"</div>
    </div>

    <q-separator />

    <div class="row">
      <div class="col-11">
        <config-tree :module-data="moduleData" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useConfigStore } from 'src/stores/config';
import { useModelsStore } from 'src/stores/models';
import { useServerStore } from 'src/stores/server';
import { useTransactionStore } from 'src/stores/transaction';
import ConfigTree from './ConfigTree.vue';

const configStore = useConfigStore();
const modelsStore = useModelsStore();
const txStore = useTransactionStore();
const serverStore = useServerStore();

const { activeNamespace } = storeToRefs(configStore);
const { loadedModels } = storeToRefs(modelsStore);
const { connected } = storeToRefs(serverStore);
const { hasTrans } = storeToRefs(txStore);

const moduleData = computed(() => {
  const ns = activeNamespace.value;
  return ns ? loadedModels.value[ns] : null;
});
</script>
