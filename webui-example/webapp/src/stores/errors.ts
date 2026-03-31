import { defineStore } from 'pinia';
import { resolveNested } from 'src/ts/CommonUtils';

export const useErrorsStore = defineStore('errors', {
  state: () => ({
    jrpcErrors: [] as any[],
    activeProblems: [] as any[],
  }),

  actions: {
    add(error: any) {
      this.jrpcErrors.unshift(error);
    },

    reset() {
      this.jrpcErrors = [];
    },

    addActive(error: any) {
      this.activeProblems.push(error);
    },

    dropActive() {
      this.activeProblems.shift();
    },

    checkResponseError(response: any) {
      const errorReason = resolveNested(response, ['data', 'error', 'data', 'reason']);
      if (errorReason) {
        this.addActive(errorReason);
      }
    },
  },
});
