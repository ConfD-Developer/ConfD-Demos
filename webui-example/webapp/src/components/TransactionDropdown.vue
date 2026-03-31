<template>
  <TooltipNeedLogin>
    <q-btn-dropdown no-caps :color="transDropdownColor" :label="transactionLabel" :disable="!connected">
      <q-form class="q-mt-xs q-pa-md q-gutter-y-sm">
        <strong>Transaction type:</strong>
        <div class="column col-12 items-center">
          <q-option-group v-model="transType" inline dense :options="transOptions" :disable="hasTrans" />
        </div>
        <q-separator />
        <div v-if="transType === 'write'" class="q-gutter-y-sm">
          <strong>Write to:</strong>
          <div class="column col-12 items-center">
            <q-option-group v-model="targetDb" dense :disable="hasTrans" :options="writeOptions" />
          </div>
          <q-separator />
        </div>
        <q-toolbar>
          <q-btn
            size="sm"
            label="new"
            :color="primaryColorWhen(!hasTrans)"
            :disable="hasTrans"
            @click="doNewTransaction"
          />
          <q-space />
          <TooltipNeedTransaction>
            <q-btn
              size="sm"
              label="delete"
              :color="primaryColorWhen(hasTrans)"
              :disable="!hasTrans"
              @click="doDeleteTransaction"
            />
          </TooltipNeedTransaction>
        </q-toolbar>
      </q-form>
    </q-btn-dropdown>
  </TooltipNeedLogin>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useModelsStore } from 'src/stores/models';
import { useServerStore } from 'src/stores/server';
import { useTransactionStore } from 'src/stores/transaction';
import TooltipNeedLogin from 'components/helpers/TooltipNeedLogin.vue';
import TooltipNeedTransaction from 'components/helpers/TooltipNeedTransaction.vue';

const serverStore = useServerStore();
const { connected, tasks } = storeToRefs(serverStore);

const transType = ref('write');
const transOptions = [
  { label: 'read', value: 'read' },
  { label: 'write', value: 'write' },
];
const targetDb = ref('running');
const writeOptions = [
  { label: 'running', value: 'running' },
  { label: 'candidate', value: 'candidate' },
];

const txStore = useTransactionStore();
const modelsStore = useModelsStore();
const { isWriteTrans, hasTrans } = storeToRefs(txStore);
const { modelsCount } = storeToRefs(modelsStore);

const transactionLabel = computed(() => {
  if (!hasTrans.value) return 'no pending transaction';
  return isWriteTrans.value ? `write to ${targetDb.value}` : 'read transaction';
});

const transDropdownColor = computed(() => {
  if (!hasTrans.value) return 'primary';
  return isWriteTrans.value ? 'orange' : 'positive';
});

function primaryColorWhen(whenCondition: boolean) {
  return whenCondition ? 'primary' : 'grey';
}

async function doNewTransaction() {
  const wantWriteTrans = transType.value === 'write';
  await tasks.value?.transaction.newTransaction(wantWriteTrans, targetDb.value);
  if (modelsCount.value < 1) {
    await tasks.value?.models.preloadModels();
  }
}

async function doDeleteTransaction() {
  await tasks.value?.transaction.deleteTransaction();
}
</script>
