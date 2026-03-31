<template>
  <TooltipNeedTransaction>
    <q-item
      clickable
      dense
      ripple
      :disable="!hasTrans"
      :active="isActive"
      active-class="bg-blue-2 text-grey-8"
      class="q-py-sm"
      @click="doActivate"
    >
      <q-item-section>
        <q-item-label>
          <q-badge>{{ modelData.name }}</q-badge>
        </q-item-label>
        <q-item-label caption lines="1">
          {{ modelData.namespace }}
        </q-item-label>
      </q-item-section>
    </q-item>
  </TooltipNeedTransaction>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useConfigStore } from 'src/stores/config';
import { useModelsStore } from 'src/stores/models';
import { useServerStore } from 'src/stores/server';
import { useTransactionStore } from 'src/stores/transaction';
import TooltipNeedTransaction from 'components/helpers/TooltipNeedTransaction.vue';

const props = defineProps<{ namespace: string }>();

const { tasks } = storeToRefs(useServerStore());
const { hasTrans } = storeToRefs(useTransactionStore());
const { loadedModels } = storeToRefs(useModelsStore());
const { activeNamespace } = storeToRefs(useConfigStore());

const modelData = computed(() => loadedModels.value[props.namespace]);
const isActive = computed(() => activeNamespace.value != null && activeNamespace.value === props.namespace);

function doActivate() {
  tasks.value?.config.activateConfig(props.namespace);
}
</script>
