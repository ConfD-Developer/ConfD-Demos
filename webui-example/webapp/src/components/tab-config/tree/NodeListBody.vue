<template>
  <div v-if="listTotal < 1">No records in list.</div>
  <div v-else>
    <div v-if="doShowPosition">showing position #{{ listPosition }} and further:</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { QTreeNode } from 'quasar';
import { updateNode } from 'src/ts/treenodes/ConfigChanges';
import { getState } from 'src/ts/treenodes/ConfigCommons';
import type { ConfigContext, ListMeta } from 'src/ts/treenodes/ConfigStateTypes';

const props = defineProps<{ context: ConfigContext; node: QTreeNode }>();

const value = computed({
  get: () => getState(props.context.state, props.node),
  set: (v: any) => updateNode(props.context, props.node, v),
});

const listData = computed(() => value.value as ListMeta | undefined);
const listTotal = computed(() => listData.value?.total ?? 0);
const listPosition = computed(() => listData.value?.position ?? -1);
const doShowPosition = computed(() => listPosition.value > -1);
</script>
