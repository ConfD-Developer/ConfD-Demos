<template>
  <div>
    <TooltipChild tooltip="apply configuration changes">
      <q-btn no-caps color="orange" label="commit" @click="doCommit()" />
    </TooltipChild>

    <q-dialog v-model="isDialogOn">
      <q-card>
        <q-card-section>
          <div v-if="commitErrors" class="q-gutter-y-sm">
            <div class="text-h6">Commit failed!</div>
            <q-separator />
            <div v-for="(error, index) in commitErrors" :key="index">
              {{ error }}
            </div>
          </div>
          <div v-else class="q-gutter-y-sm">
            <div class="text-h6">Successful commit!<br />(write transaction closed)</div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useServerStore } from 'src/stores/server';
import TooltipChild from 'components/helpers/TooltipChild.vue';

const isDialogOn = ref(false);
const commitErrors = ref<unknown>(null);
const emit = defineEmits<{ (e: 'commit'): void }>();
const { tasks } = storeToRefs(useServerStore());

function doCommit() {
  void (async () => {
    commitErrors.value = null;
    try {
      await tasks.value?.transaction.commit.validateCommit();
      await tasks.value?.transaction.commit.commit();
      emit('commit');
    } catch (errors: any) {
      commitErrors.value = errors;
    } finally {
      isDialogOn.value = true;
    }
  })();
}
</script>
