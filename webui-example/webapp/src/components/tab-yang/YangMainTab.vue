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
      <yang-list />
    </q-drawer>
    <yang-details />
  </div>
</template>

<script setup lang="ts">
import YangDetails from './YangDetails.vue'
import YangList from './YangList.vue'
</script>
