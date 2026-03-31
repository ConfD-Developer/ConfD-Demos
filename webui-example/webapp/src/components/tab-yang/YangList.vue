<template>
  <q-scroll-area class="fit">
    <q-list separator>
      <!-- list "header" - button for models download/refresh -->
      <q-item>
        <q-item-section>{{ modelsCount }} device models:</q-item-section>
        <q-item-section avatar>
          <TooltipNeedLogin>
            <q-btn dense size="sm" icon="refresh" :disable="!connected" :color="refreshColor" @click="doGetModels">
              <q-tooltip>Get models from device</q-tooltip>
            </q-btn>
          </TooltipNeedLogin>
        </q-item-section>
      </q-item>

      <q-separator class="q-mb-sm" />

      <!-- models infomation downloaded from device -->
      <div v-if="gotModels">
        <yang-list-item v-for="(val, index) in loadedModels" :key="index" :namespace="index" />
      </div>
      <div v-else class="text-center text-h6 q-mt-lg">didn't load<br />from device yet</div>
    </q-list>
  </q-scroll-area>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useModelsStore } from 'src/stores/models';
import { useServerStore } from 'src/stores/server';
import { useTransactionStore } from 'src/stores/transaction';
import YangListItem from './YangListItem.vue';
import TooltipNeedLogin from 'components/helpers/TooltipNeedLogin.vue';

const modelsStore = useModelsStore();
const serverStore = useServerStore();
const txStore = useTransactionStore();
const { connected, tasks } = storeToRefs(serverStore);
const { loadedModels } = storeToRefs(modelsStore);

const modelsCount = computed(() => Object.keys(loadedModels.value).length);
const gotModels = computed(() => modelsCount.value > 0);
const { hasTrans } = storeToRefs(txStore);
const refreshColor = computed(() => (hasTrans.value && modelsCount.value < 1 ? 'orange' : 'primary'));

async function doGetModels() {
  await tasks.value?.models.loadModelsToStore();
}
</script>
