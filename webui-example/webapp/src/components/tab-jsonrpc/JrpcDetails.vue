<template>
  <div v-if="activeIndex < 0" class="q-mt-lg text-center text-h6">
    Pick a dispatched/processed JSON-RPC message in menu on the left.
  </div>
  <div v-else class="column">
    <q-toolbar>
      <div class="row text-h6">
        Details for JSON-RPC message
        <q-chip square outline :label="'#' + jsonRequest['id']" />
        :
      </div>
      <q-space />
      <div class="row items-baseline q-gutter-x-sm">
        <div>response status:</div>
        <div class="text-h6">{{ activeMessage['status'] }} - {{ activeMessage['statusText'] }}</div>
      </div>
    </q-toolbar>

    <q-tabs
      v-model="activeTab"
      dense
      class="q-mt-md text-grey"
      active-color="primary"
      indicator-color="primary"
      align="justify"
      narrow-indicator
    >
      <q-tab no-caps name="payload" label="JSON-RPC payload" />
      <q-tab no-caps name="raw" label="AXIOS response dump" />
    </q-tabs>

    <q-separator class="q-mb-lg" />

    <q-tab-panels v-model="activeTab">
      <q-tab-panel name="payload" class="q-gutter-y-sm">
        <div class="text-h6">Request:</div>
        <div>
          <CodeBlock :text="jsonRequest" />
        </div>
        <div class="text-h6">Response:</div>
        <div>
          <CodeBlock :text="jsonResponse" />
        </div>
      </q-tab-panel>

      <q-tab-panel name="raw" class="q-gutter-y-sm">
        <div class="text-h6">Raw dump:</div>
        <div>
          <CodeBlock :text="activeMessage" />
        </div>
      </q-tab-panel>
    </q-tab-panels>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useResponsesStore } from 'src/stores/responses';
import CodeBlock from 'components/helpers/CodeBlock.vue';

const responsesStore = useResponsesStore();
const { activeIndex, jrpcResponses } = storeToRefs(responsesStore);

const activeTab = ref('payload');

const activeMessage = computed<any>(() => {
  let msg = jrpcResponses.value[activeIndex.value];
  if (msg && 'response' in msg) {
    msg = msg['response'];
  }
  return msg ?? {};
});

const jsonRequest = computed(() => {
  const requestString = activeMessage.value['config']?.['data'];
  return requestString ? JSON.parse(requestString) : {};
});

const jsonResponse = computed(() => activeMessage.value['data']);
</script>
