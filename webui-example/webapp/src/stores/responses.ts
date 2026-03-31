import { defineStore } from 'pinia';

export const useResponsesStore = defineStore('responses', {
  state: () => ({
    jrpcResponses: [] as any[],
    activeIndex: -1 as number,
  }),

  actions: {
    add(response: any) {
      this.jrpcResponses.unshift(response);
    },
    activate(index: number) {
      this.activeIndex = index;
    },
    reset() {
      this.jrpcResponses = [];
      this.activeIndex = -1;
    },
  },
});
