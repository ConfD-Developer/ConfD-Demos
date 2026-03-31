import { useModelsStore } from 'src/stores/models';
import { useConfigStore } from 'src/stores/config';
import { TasksBase } from './TasksBase';

export default class TasksModel extends TasksBase {
  // get list of all models on device - basic info only
  async loadModelsToStore(): Promise<void> {
    const modelsStore = useModelsStore();
    const configStore = useConfigStore();
    const response: any = await this.jrpc().general.get_system_settings('models');

    modelsStore.reset();
    configStore.reset();
    const modelsArr = response['data']['result'];
    for (const i in modelsArr) {
      modelsStore.add(modelsArr[i]);
    }
  }

  // get details for specified namespace model
  // and activate it for display in UI
  async activateModel(namespace: string): Promise<void> {
    await this.getModelDetails(namespace);
    const modelsStore = useModelsStore();
    modelsStore.activate(namespace);
  }

  // preload all models information to store
  async preloadModels(): Promise<void> {
    await this.loadModelsToStore();
    await this.getAllDetails();
  }

  async getModelDetails(namespace: string): Promise<void> {
    const modelsStore = useModelsStore();
    const response: any = await this.jrpc().schema.getSchemaByNamespace(this.th(), namespace);
    const payload = {
      namespace,
      schema: response['data']['result'],
    };
    modelsStore.addDetails(payload);
  }

  async getAllDetails(): Promise<void> {
    const modelsStore = useModelsStore();
    const loadedModels = modelsStore.loadedModels;
    await Promise.all(
      Object.keys(loadedModels).map((ns) => {
        return this.getModelDetails(ns);
      }),
    );
  }
}
