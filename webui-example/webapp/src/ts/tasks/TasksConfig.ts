import { useConfigStore } from 'src/stores/config';

export default class TasksConfig {
  activateConfig(namespace: string) {
    const configStore = useConfigStore();
    configStore.activate(namespace);
  }
}
