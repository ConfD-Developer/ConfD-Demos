<template>
  <div>
    <TooltipChild tooltip="validate transaction">
      <q-btn no-caps color="primary" label="validate" @click="doValidate()" />
    </TooltipChild>

    <q-dialog v-model="isDialogOn">
      <q-card>
        <q-card-section>
          <div v-if="validationErrors" class="q-gutter-y-sm">
            <div class="text-h6">
              {{ failedLabel }}
            </div>
            <q-separator />
            <div v-for="(error, index) in validationErrors" :key="index">
              {{ error }}
            </div>
          </div>
          <div v-else class="q-gutter-y-sm">
            <div class="text-h6">Transaction validated OK.</div>
            <div v-if="validationWarnings">
              <div v-for="(warning, index) in validationWarnings" :key="index">
                {{ warning }}
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useServerStore } from 'src/stores/server';
import TooltipChild from 'components/helpers/TooltipChild.vue';

const isDialogOn = ref(false);
const validationErrors = ref<any[] | null>(null);
const validationWarnings = ref<any[] | null>(null);
const { tasks } = storeToRefs(useServerStore());

const failedLabel = computed(() => {
  const errorsCount = validationErrors.value && validationErrors.value.length ? validationErrors.value.length : 0;
  const verb = errorsCount === 1 ? 'is' : 'are';
  const plural = errorsCount === 1 ? '' : 's';
  const label = `There ${verb} following issue${plural}:`;
  return `Validation failed! ${label}`;
});

const doValidate = async () => {
  validationErrors.value = null;
  validationWarnings.value = null;
  try {
    validationWarnings.value = await tasks.value?.transaction.changes.validateTransaction();
  } catch (errors: any) {
    validationErrors.value = errors;
  } finally {
    isDialogOn.value = true;
  }
};
</script>
