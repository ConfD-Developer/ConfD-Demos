<template>
  <div v-if="isWriteTrans" class="items-center">
    <TooltipChild tooltip="show transaction changes" anchor="top left">
      <q-btn dense no-caps icon="done_all" color="orange" @click="doShowChanges()" />
    </TooltipChild>

    <q-dialog v-model="changesDialog">
      <q-card>
        <q-card-section class="row items-center">
          <template v-if="changesData">
            <transaction-changes-list :changes="changesData" />
          </template>
          <template v-else>
            <div class="t ext-h6">No transaction changes yet.</div>
          </template>
        </q-card-section>
        <q-separator />
        <q-card-section v-if="gotChanges" class="row q-gutter-x-sm">
          <TransactionValidateDialog />
          <q-space />
          <TransactionCommitDialog @commit="doCommit()" />
        </q-card-section>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { Notify } from 'quasar';
import { useErrorsStore } from 'src/stores/errors';
import { useServerStore } from 'src/stores/server';
import { useTransactionStore } from 'src/stores/transaction';
import { type TransactionChange } from 'src/ts/tasks/TasksTransactionChanges';
import TransactionChangesList from './TransactionChangesList.vue';
import TransactionCommitDialog from './TransactionCommitDialog.vue';
import TransactionValidateDialog from './TransactionValidateDialog.vue';
import TooltipChild from 'components/helpers/TooltipChild.vue';

const transactionStore = useTransactionStore();
const errorsStore = useErrorsStore();
const { tasks } = storeToRefs(useServerStore());
const { isWriteTrans } = storeToRefs(transactionStore);

const changesDialog = ref(false);
const changesData = ref<TransactionChange[] | null>(null);

const gotChanges = computed(() => !!(changesData.value && changesData.value.length > 0));

function doShowChanges() {
  void (async () => {
    try {
      const response = await tasks.value?.transaction.changes.getTransChanges();
      changesData.value = response ?? null;
      changesDialog.value = true;
    } catch (error) {
      Notify.create({
        type: 'negative',
        message: JSON.stringify(error),
      });
      changesData.value = null;
    }
  })();
}

function doCommit() {
  changesData.value = null;
  changesDialog.value = false;
  errorsStore.addActive('Successful commit!\n(write transaction closed)');
  tasks.value?.transaction.resetTransaction();
}
</script>
