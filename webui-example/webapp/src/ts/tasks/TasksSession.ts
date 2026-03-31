import ConfdJrpcDispatcher from '../confd-json-rpc/confd-jrpc-dispatcher';
import { useServerStore } from 'src/stores/server';
import { useErrorsStore } from 'src/stores/errors';
import { useConfigStore } from 'src/stores/config';
import { useDblocksStore } from 'src/stores/dblocks';
import { useModelsStore } from 'src/stores/models';
import { useResponsesStore } from 'src/stores/responses';
import { useTransactionStore } from 'src/stores/transaction';
import { TasksBase } from './TasksBase';

export default class TasksSession extends TasksBase {
  async login({ user, password }: { user: string; password: string }): Promise<void> {
    const serverStore = useServerStore();
    const errorsStore = useErrorsStore();
    const host = process.env.PROD ? location.origin : serverStore.loginInfo.host;
    const dispatcher = new ConfdJrpcDispatcher(host);
    const response: any = await dispatcher.session.login(user, password);

    if (wasLoginOk(response)) {
      const payload = { host, user, password, dispatcher };
      serverStore.loggedIn(payload);
    } else {
      errorsStore.checkResponseError(response);
    }
  }

  async logout(): Promise<void> {
    const serverStore = useServerStore();
    const configStore = useConfigStore();
    const dblocksStore = useDblocksStore();
    const errorsStore = useErrorsStore();
    const modelsStore = useModelsStore();
    const responsesStore = useResponsesStore();
    const transactionStore = useTransactionStore();
    const doReset = () => {
      configStore.reset();
      dblocksStore.reset();
      errorsStore.reset();
      modelsStore.reset();
      responsesStore.reset();
      transactionStore.reset();
    };

    if (serverStore.connected) {
      await this.jrpc().session.logout();
    }

    doReset();
    serverStore.loggedOut();
  }
}

function wasLoginOk(response: any): boolean {
  const data = response['data'];
  const gotError = 'error' in data;
  return !gotError;
}
