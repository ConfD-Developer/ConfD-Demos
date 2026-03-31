<template>
  <q-list separator>
    <q-item>
      <q-item-section class="text-h6"> Pending transaction changes reported by ConfD: </q-item-section>
    </q-item>

    <q-item v-for="(change, index) in props.changes" :key="index">
      <q-item-section avatar>
        <q-icon :name="opIcon(change)" :label="opLabel(change)" />
      </q-item-section>

      <q-item-section>
        <q-item-label overline class="no-wrap">
          {{ change.path }}
        </q-item-label>
        <q-item-label>
          <div class="row">
            {{ change.label }}
            <div v-if="'old' in change || isOpSet(change)" class="q-ml-xs">
              from "{{ change.old }}" to "{{ change.value }}"
            </div>
          </div>
        </q-item-label>
      </q-item-section>
    </q-item>
  </q-list>
</template>

<script setup lang="ts">
import { type TransactionChange } from 'src/ts/tasks/TasksTransactionChanges';

const props = defineProps<{ changes: TransactionChange[] }>();

function opLabel(change: TransactionChange) {
  return opMap[change.op].label;
}
function opIcon(change: TransactionChange) {
  return opMap[change.op].icon;
}
function isOpSet(change: TransactionChange) {
  return change.op === 'value_set';
}

const opMap: Record<TransactionChange['op'], { icon: string; label: string }> = {
  created: { icon: 'add_circle', label: 'created' },
  deleted: { icon: 'remove_circle', label: 'deleted' },
  modified: { icon: 'build', label: 'modified' },
  value_set: { icon: 'edit', label: 'changed' },
};
</script>
