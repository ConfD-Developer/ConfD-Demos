<template>
  <q-scroll-area class="fit">
    <q-list separator>
      <!-- list "header" - button for models download/refresh -->
      <q-item>
        <q-item-section>{{ modelsCount }} config models:</q-item-section>
        <q-item-section avatar>
          <TooltipNeedTransaction>
            <q-btn dense size="sm" icon="refresh" :disable="!hasTrans" :color="refreshColor" @click="doGetConfigModels">
              <q-tooltip>Get list of configs from device</q-tooltip>
            </q-btn>
          </TooltipNeedTransaction>
        </q-item-section>
      </q-item>

      <q-separator class="q-mb-sm" />

      <!-- models infomation downloaded from device -->
      <div v-if="modelsCount > 0">
        <config-list-item v-for="(val, index) in modelsWithNodes" :key="index" :namespace="index" />
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
import ConfigListItem from './ConfigListItem.vue';
import TooltipNeedTransaction from 'components/helpers/TooltipNeedTransaction.vue';

const modelsStore = useModelsStore();
const { tasks } = storeToRefs(useServerStore());

const { modelsWithNodes } = storeToRefs(modelsStore);
const txStore = useTransactionStore();

const modelsCount = computed(() => Object.keys(modelsWithNodes.value).length);
const { hasTrans } = storeToRefs(txStore);
const refreshColor = computed(() => (hasTrans.value && modelsCount.value < 1 ? 'orange' : 'primary'));

async function doGetConfigModels() {
  await tasks.value?.models.preloadModels();
}
</script>
