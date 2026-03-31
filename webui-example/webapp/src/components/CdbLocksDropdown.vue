<!--
  CDB locks handling:
  show, change, and track the lock status of ConfD CDB databases.
-->
<template>
  <TooltipNeedLogin>
    <q-btn-dropdown no-caps :disable="!connected" :color="locksDropdownColor">
      <template v-slot:default>
        <div v-for="(lockName, index) in lockNames" :key="index">
          <cdb-lock :target-db="lockName" />
          <q-separator />
        </div>
      </template>
      <template v-slot:label>
        <div class="row items-center q-gutter-x-sm no-wrap">
          <div v-show="isSomeLocked">
            <q-icon :name="locksIcon" size="xs" />
          </div>
          <div>
            {{ locksLabel }}
          </div>
        </div>
      </template>
    </q-btn-dropdown>
  </TooltipNeedLogin>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useDblocksStore } from 'src/stores/dblocks';
import { useServerStore } from 'src/stores/server';
import CdbLock from './CdbLock.vue';
import TooltipNeedLogin from 'components/helpers/TooltipNeedLogin.vue';

const lockNames = ref(['running', 'candidate']);

const { connected } = storeToRefs(useServerStore());
const { lockedDbNames } = storeToRefs(useDblocksStore());

const isSomeLocked = computed(() => lockedDbNames.value.length > 0);
const locksLabel = computed(() => (isSomeLocked.value ? lockedDbNames.value.join(', ') : 'no DB locks'));
const locksIcon = computed(() => (isSomeLocked.value ? 'lock' : ''));
const locksDropdownColor = computed(() => (isSomeLocked.value ? 'orange' : 'primary'));
</script>
