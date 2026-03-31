import { defineStore } from 'pinia';

export const useConfigStore = defineStore('config', {
  state: () => ({
    activeNamespace: null as string | null,
  }),

  actions: {
    activate(namespace: string) {
      this.activeNamespace = namespace;
    },

    reset() {
      this.activeNamespace = null;
    },
  },
});
