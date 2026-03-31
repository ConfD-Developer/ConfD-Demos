import { defineStore } from 'pinia';
import { markRaw } from 'vue';
import TaskHandler from 'src/ts/tasks/TaskHandler';
import type ConfdJrpcDispatcher from 'src/ts/confd-json-rpc/confd-jrpc-dispatcher';

export const useServerStore = defineStore('server', {
  state: () => ({
    loginInfo: {
      host: process.env.PROD ? 'https://localhost:8888' : 'http://localhost:8080',
      user: 'admin',
      password: 'admin',
    },

    connected: false as boolean,

    dispatcher: null as ConfdJrpcDispatcher | null,
    tasks: new TaskHandler(),
  }),

  actions: {
    setTasks(tasks: TaskHandler) {
      this.tasks = tasks;
    },

    setLoginInfo(payload: { host: string; user: string; password: string }) {
      this.loginInfo = { ...this.loginInfo, ...payload };
    },

    setDispatcher(dispatcher: ConfdJrpcDispatcher | null) {
      // this.dispatcher = dispatcher ? markRaw(dispatcher) : null;
      this.dispatcher = dispatcher ? markRaw(dispatcher) : null;
    },

    loggedIn({ host, user, password, dispatcher }: { host: string; user: string; password: string; dispatcher?: any }) {
      this.setLoginInfo({ host, user, password });
      this.setDispatcher(dispatcher);
      this.connected = true;
    },

    loggedOut() {
      this.setDispatcher(null);
      this.connected = false;
    },
  },
});
