<template>
  <div class="q-px-md q-py-sm row q-gutter-x-md items-center">
    <strong>{{ props.targetDb }} DB is:</strong>
    <q-space />

    <div>
      <q-icon :name="isLocked ? 'lock' : 'lock_open'" size="xs" />
      {{ isLocked ? 'locked' : 'not locked' }}
    </div>

    <TooltipCode v-if="formattedFailure" :tooltip="formattedFailure">
      <q-icon name="error" size="xs" :color="errorColor" @mouseover="locksStore.setShown(props.targetDb)" />
    </TooltipCode>
    <q-space />

    <q-btn dense no-caps :label="isLocked ? 'unlock' : 'lock'" @click="switchLock" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useDblocksStore } from 'src/stores/dblocks';
import { useServerStore } from 'src/stores/server';
import TooltipCode from 'components/helpers/TooltipCode.vue';

const props = defineProps<{ targetDb: string }>();

const locksStore = useDblocksStore();

const { locks } = storeToRefs(locksStore);

const lockRecord = computed(() => locks.value.get(props.targetDb));

const isLocked = computed(() => {
  if (!lockRecord.value) return false;
  if ('error' in lockRecord.value.result) return false;
  return lockRecord.value.result.locked;
});

const formattedFailure = computed(() => {
  const result = lockRecord.value?.result;
  if (!result || !('error' in result)) return undefined;
  return `Lock attempt failed at:\n\t${lockRecord.value.date};\nDue to:\n\t${result.error}`;
});

const errorColor = computed(() => (lockRecord.value?.shown ? '' : 'red'));

const { tasks } = storeToRefs(useServerStore());

const switchLock = async () => {
  const targetDb = props.targetDb;
  const lockState = !isLocked.value;
  try {
    await tasks.value?.database.setLockState(targetDb, lockState);
    locksStore.setSuccess(targetDb, lockState);
  } catch (error: any) {
    const message = error?.message ?? 'Database lock operation failed';
    const sessions = error?.sessions ?? '';
    const failReason = `${message} - ${sessions}`;
    locksStore.setFailure(targetDb, failReason);
  }
};
</script>
