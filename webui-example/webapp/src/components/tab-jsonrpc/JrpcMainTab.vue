<template>
  <div>
    <q-drawer bordered side="left" :width="240" show-if-above :breakpoint="480" :value="true">
      <jrpc-list />
    </q-drawer>

    <jrpc-details />
  </div>
</template>

<script setup lang="ts">
import JrpcDetails from './JrpcDetails.vue';
import JrpcList from './JrpcList.vue';
</script>
