<template>
  <q-page>
    <ActiveErrorDialog />

    <q-tab-panels v-model="activeTabName" keep-alive>
      <q-tab-panel
        v-for="tabData in applicationTabs"
        :key="tabData.name"
        :name="tabData.name"
      >
        <component :is="tabData.component" />
      </q-tab-panel>
    </q-tab-panels>
  </q-page>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import type { Ref } from 'vue'
import ActiveErrorDialog from 'src/components/ActiveErrorDialog.vue'

const applicationTabs = inject('applicationTabs') as Ref<any[]>
const activeTabName = inject('activeTabName') as Ref<string>
</script>
