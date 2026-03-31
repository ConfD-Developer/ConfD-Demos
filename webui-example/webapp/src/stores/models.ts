import { defineStore } from 'pinia';
import type { YangSchemaNode } from 'src/ts/YangSchemaTypes';

export const useModelsStore = defineStore('models', {
  state: () => ({
    loadedModels: {} as Record<string, any>,
    modelsCount: 0 as number,
    activeNamespace: null as string | null,
  }),

  getters: {
    modelsWithNodes: (state) => {
      const result: Record<string, any> = {};
      for (const ns in state.loadedModels) {
        const model = state.loadedModels[ns];
        if (model.hasModule) {
          result[ns] = model;
        }
      }
      return result;
    },
  },

  actions: {
    activate(namespace: string) {
      this.activeNamespace = namespace;
    },

    add(modelSchema: YangSchemaNode) {
      const newModel = {
        ...modelSchema,
        schema: null,
        hasModule: false,
      };

      const namespace = modelSchema['namespace'];
      if (!(namespace in this.loadedModels)) {
        this.modelsCount = this.modelsCount + 1;
      }

      this.loadedModels[namespace] = newModel;
    },

    addDetails({ namespace, schema }: { namespace: string; schema: YangSchemaNode }) {
      const modelData = this.loadedModels[namespace];
      modelData.schema = schema;
      const hasModule = schema && schema['data']['children'].length > 0;
      modelData.hasModule = hasModule;
    },

    reset() {
      this.loadedModels = {};
      this.modelsCount = 0;
      this.activeNamespace = null;
    },
  },
});
