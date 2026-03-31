<template>
  <div>
    <q-drawer
      side="left"
      bordered
      :width="240"
      show-if-above
      :breakpoint="480"
      :value="true"
    >
      <config-list />
    </q-drawer>
    <config-details />
  </div>
</template>

<script setup lang="ts">
import ConfigDetails from './ConfigDetails.vue'
import ConfigList from './ConfigList.vue'
</script>
