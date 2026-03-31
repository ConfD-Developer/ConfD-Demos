<template>
  <q-item clickable dense active-class="bg-blue-2 text-blue-8" :active="isActive" @click="doActivate">
    <q-item-section avatar>
      <q-badge align="middle" color="primary"> #{{ requestJson['id'] }} </q-badge>
    </q-item-section>
    <q-item-section>
      {{ requestJson['method'] }}
    </q-item-section>
  </q-item>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useResponsesStore } from 'src/stores/responses';

const props = defineProps<{ jrpcData: Record<string, any>; queueIndex: number }>();

const responsesStore = useResponsesStore();
const { activeIndex } = storeToRefs(responsesStore);

const isActive = computed(() => activeIndex.value === props.queueIndex);
const requestJson = computed(() => JSON.parse(props.jrpcData['config']['data']));

function doActivate() {
  responsesStore.activate(props.queueIndex);
}
</script>
