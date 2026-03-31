<template>
  <q-dialog v-model="isShown" persistent>
    <q-card>
      <q-card-section class="text-h6">
        {{ currentProblem }}
      </q-card-section>
      <q-card-actions align="center">
        <q-btn dense label="OK" color="primary" @click="doClose()" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useErrorsStore } from 'src/stores/errors';

const isShown = ref(false);
const errorsStore = useErrorsStore();

const { activeProblems } = storeToRefs(errorsStore);
const problemsLeft = computed(() => activeProblems.value.length);
const currentProblem = computed(() => (problemsLeft.value > 0 ? activeProblems.value[0] : ''));

watch(problemsLeft, (count) => {
  if (count > 0) isShown.value = true;
});

function doClose() {
  isShown.value = false;
  errorsStore.dropActive();
}
</script>
