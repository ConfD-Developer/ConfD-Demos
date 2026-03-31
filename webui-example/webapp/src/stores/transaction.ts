import { defineStore } from 'pinia';

export const useTransactionStore = defineStore('transaction', {
  state: () => ({
    transHandle: -1,
    isWriteTrans: false,
  }),

  getters: {
    hasTrans: (state) => state.transHandle !== -1,
  },

  actions: {
    setHandle(th: number) {
      this.transHandle = th;
    },

    setIsWrite(isWrite: boolean) {
      this.isWriteTrans = isWrite;
    },

    reset() {
      this.transHandle = -1;
      this.isWriteTrans = false;
    },

    newPendingTransaction({ handle, isWriteTrans }: { handle: number; isWriteTrans: boolean }) {
      this.setHandle(handle);
      this.setIsWrite(isWriteTrans);
    },
  },
});
