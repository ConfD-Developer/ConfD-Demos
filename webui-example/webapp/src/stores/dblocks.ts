import { defineStore } from 'pinia';

interface LockResult {
  date: string;
  result: { locked: boolean } | { error: string };
  shown: boolean;
}

export const useDblocksStore = defineStore('dblocks', {
  state: () => ({
    locks: new Map<string, LockResult>(),
  }),

  getters: {
    lockedDbNames: (state) => {
      const names: string[] = [];
      for (const [name, lock] of state.locks.entries()) {
        if ('locked' in lock.result && lock.result.locked === true) {
          names.push(name);
        }
      }
      return names;
    },
  },

  actions: {
    setSuccess(dbName: string, locked: boolean) {
      this.locks.set(dbName, {
        date: new Date().toISOString(),
        shown: false,
        result: { locked },
      });
    },

    setFailure(dbName: string, error: string) {
      this.locks.set(dbName, {
        date: new Date().toISOString(),
        shown: false,
        result: { error },
      });
    },

    setShown(dbName: string) {
      if (!this.locks.has(dbName)) return;
      this.locks.set(dbName, { ...this.locks.get(dbName)!, shown: true });
    },

    reset() {
      this.locks = new Map();
    },
  },
});
