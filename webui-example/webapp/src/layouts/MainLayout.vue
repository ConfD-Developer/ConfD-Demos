<!--
  The main/whole application component.
  Includes all there is to be shown on screen.
-->
<template>
  <q-layout view="hHh Lpr fff">
    <q-header
      class="bg-white"
      height-hint="100"
    >
      <q-toolbar class="bg-primary text-white q-gutter-x-md">
        <!-- main app title -->
        <q-toolbar-title class="col-auto">
          ConfD JSON-RPC example UI
        </q-toolbar-title>

        <q-space />

        <!-- application tabs switching main contents of screen -->
        <q-tabs shrink>
          <q-route-tab :to="{ name: 'config' }" label="Device config" />
          <q-route-tab :to="{ name: 'yang' }" label="YANG schemas" />
          <q-route-tab :to="{ name: 'jrpc' }" label="JSON-RPC">
            <q-badge
              v-if="isBadgeVisible"
              floating
              color="secondary"
              :label="jrpcCount"
            />
          </q-route-tab>
        </q-tabs>
        <q-space />

        <!-- dialog for error display (if any encountered) -->
        <ErrorsDialog />

        <q-space />

        <!-- transaction commit/validation/ etc. controls -->
        <TransactionControls />

        <!-- ConfD CDB locks UI -->
        <CdbLocksDropdown />

        <!-- read/write transaction UI -->
        <TransactionDropdown />

        <!-- target ConfD server login UI -->
        <LoginDropdown />
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>

    <WarningDialog />
  </q-layout>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount } from 'vue';
import { storeToRefs } from 'pinia';
import { useResponsesStore } from 'src/stores/responses';
import { useServerStore } from 'src/stores/server';
import CdbLocksDropdown from 'src/components/CdbLocksDropdown.vue';
import ErrorsDialog from 'src/components/ErrorsDialog.vue';
import TransactionControls from 'src/components/tab-config/TransactionControls.vue';
import TransactionDropdown from 'src/components/TransactionDropdown.vue';
import LoginDropdown from 'src/components/LoginDropdown.vue';
import WarningDialog from 'src/components/WarningDialog.vue';

const responsesStore = useResponsesStore();
const serverStore = useServerStore();
const { connected, tasks } = storeToRefs(serverStore);
const { jrpcResponses } = storeToRefs(responsesStore);

const jrpcCount = computed(() => jrpcResponses.value.length);
const isBadgeVisible = computed(() => jrpcCount.value > 0);

async function releaseSession() {
  const isLoggedIn = connected.value;
  if (isLoggedIn && tasks.value?.session) {
    await tasks.value.session.logout();
  }
}

function onBeforeUnload() {
  void releaseSession();
}

onMounted(() => window.addEventListener('beforeunload', onBeforeUnload));
onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload));
</script>
