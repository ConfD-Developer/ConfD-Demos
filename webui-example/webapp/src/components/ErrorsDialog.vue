<template>
  <div>
    <q-btn v-if="errorCount > 0" dense flat icon="error_outline" @click="showErrors = true">
      <q-badge v-if="errorCount" floating color="red">
        {{ errorCount }}
      </q-badge>
    </q-btn>

    <q-dialog v-model="showErrors">
      <q-card>
        <q-card-section class="row q-gutter-y-sm">
          <div class="text-h6">
            JSON-RPC errors reported by ConfD and/or Axios:
            <q-separator />
          </div>

          <div v-if="errorCount < 1">none currently logged</div>

          <div v-for="(val, index) in jrpcErrors" :key="index">
            <CodeBlock :text="val" />
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn
            v-if="errorCount > 0"
            no-caps
            color="primary"
            icon="delete_forever"
            label="drop all errors"
            @click="doFlushErrors()"
          />
          <q-space />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useErrorsStore } from 'src/stores/errors';
import CodeBlock from 'components/helpers/CodeBlock.vue';

const showErrors = ref(false);
const errorsStore = useErrorsStore();
const { jrpcErrors } = storeToRefs(errorsStore);

const errorCount = computed(() => jrpcErrors.value.length);

function doFlushErrors() {
  errorsStore.reset();
}
</script>
