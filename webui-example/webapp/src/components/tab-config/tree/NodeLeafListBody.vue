<template>
  <div class="col-12 items-baseline q-gutter-x-xs">
    <q-expansion-item v-model="expState" dense icon="view_headline" :label="expansionLabel">
      <div v-for="(val, index) in value" :key="index">
        <q-chip
          :clickable="false"
          :color="badgeColor"
          dense
          :label="val"
          outline
          square
          :removable="tnIsEditable"
          size="md"
          @remove="doDeleteLeafListEntry(val)"
        />
      </div>
    </q-expansion-item>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { QTreeNode } from 'quasar';
import { useTreeNode } from './useTreeNode';
import { deleteLeafListEntry } from 'src/ts/treenodes/ConfigChanges';
import type { ConfigContext } from 'src/ts/treenodes/ConfigStateTypes';

const props = defineProps<{ context: ConfigContext; node: QTreeNode }>();

const { value, tnIsConfigFalse, tnIsEditable } = useTreeNode({
  context: props.context,
  node: props.node,
});

const expState = ref(false);

const elemsCount = computed(() => {
  const val = value.value;
  return val ? val.length : 0;
});

const badgeColor = computed(() => (tnIsConfigFalse.value ? 'secondary' : 'black'));

const expansionLabel = computed(() => {
  const count = elemsCount.value;
  const singular = count === 1 ? '' : 's';
  const labelCount = `${count} configured value${singular}`;

  const stateStr = expState.value ? 'collapse' : 'expand';
  const labelHint = count > 0 ? `(click to ${stateStr})` : '';

  return [labelCount, labelHint].join(' ');
});

function doDeleteLeafListEntry(val: any) {
  deleteLeafListEntry(props.context, props.node, val);
}
</script>
