<template>
  <q-btn-dropdown no-caps :color="connectedColor" :label="connectedLabel">
    <q-form class="q-mt-xs q-pa-md q-gutter-y-sm">
      <strong>JSON-RPC server:</strong>
      <q-input v-model="form.user" outlined label="user" :disable="connected" />
      <q-input v-model="form.password" outlined label="password" type="password" :disable="connected" />

      <q-toolbar>
        <q-btn size="sm" label="login" :color="activeColor(!connected)" :disable="connected" @click="doLogin" />
        <q-space />
        <TooltipNeedLogin>
          <q-btn size="sm" label="logout" :color="activeColor(connected)" :disable="!connected" @click="doLogout" />
        </TooltipNeedLogin>
      </q-toolbar>
    </q-form>
  </q-btn-dropdown>
</template>

<script setup lang="ts">
import { reactive, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useServerStore } from 'src/stores/server';
import TooltipNeedLogin from 'components/helpers/TooltipNeedLogin.vue';

const form = reactive({ user: '', password: '' });
const serverStore = useServerStore();
const { connected, tasks } = storeToRefs(serverStore);

const connectedLabel = computed(() => (connected.value ? 'connected' : 'disconnected'));
const connectedColor = computed(() => (connected.value ? 'positive' : 'negative'));

const loginInfo = serverStore.loginInfo;
form.user = loginInfo.user;
form.password = loginInfo.password;

function activeColor(isActive: boolean) {
  return isActive ? 'primary' : 'grey';
}
async function doLogin() {
  await tasks.value?.session.login(form);
}
async function doLogout() {
  await tasks.value?.session.logout();
}
</script>
