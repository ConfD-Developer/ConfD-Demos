<template>
  <q-list>
    <q-item>
      <q-item-section> {{ responseCount }} logged JSON-RPCs </q-item-section>
      <q-item-section v-if="responseCount > 0" avatar>
        <TooltipChild tooltip="Empty the queue!">
          <q-btn dense size="sm" icon="delete_forever" @click="responsesStore.reset()" />
        </TooltipChild>
      </q-item-section>
    </q-item>

    <q-separator class="q-mb-sm" />

    <div v-if="responseCount > 0">
      <jrpc-list-item v-for="(val, index) in jrpcResponses" :key="index" :jrpc-data="val" :queue-index="index" />
    </div>
    <div v-else class="text-center text-h6 q-mt-lg">none in queue</div>
  </q-list>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useResponsesStore } from 'src/stores/responses';
import JrpcListItem from './JrpcListItem.vue';
import TooltipChild from 'components/helpers/TooltipChild.vue';

const responsesStore = useResponsesStore();

const { jrpcResponses } = storeToRefs(responsesStore);
const responseCount = computed(() => jrpcResponses.value.length);
</script>
