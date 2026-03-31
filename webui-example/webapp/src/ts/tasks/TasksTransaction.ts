import { useErrorsStore } from 'src/stores/errors';
import { useConfigStore } from 'src/stores/config';
import { useTransactionStore } from 'src/stores/transaction';
import { resolveNested } from '../CommonUtils';
import { TasksBase } from './TasksBase';

export default class TasksTransaction extends TasksBase {
  async newTransaction(isWriteTrans: boolean, targetDb: string): Promise<any> {
    const response: any = await this.newSimpleTrans(isWriteTrans, targetDb);
    const data = response['data'];

    if ('error' in data) {
      const errorMessage = resolveNested(data, ['error', 'message']);
      const errorsStore = useErrorsStore();
      errorsStore.addActive(errorMessage || data);
      return -1;
    }

    const handle = resolveNested(data, ['result', 'th']);
    const transactionStore = useTransactionStore();
    const payload = { handle, isWriteTrans };
    return transactionStore.newPendingTransaction(payload);
  }

  async deleteTransaction(): Promise<void> {
    const transactionStore = useTransactionStore();
    const configStore = useConfigStore();
    await this.jrpc().transaction.delete_trans(this.th());
    configStore.reset();
    transactionStore.reset();
  }

  // drop transaction info
  // to be used when ConfD automatically drops transaction on commit
  resetTransaction() {
    const configStore = useConfigStore();
    configStore.reset();
    const transactionStore = useTransactionStore();
    transactionStore.reset();
  }

  async newSimpleTrans(isWrite: boolean, targetDb: string): Promise<any> {
    const params = {
      db: targetDb,
      mode: isWrite ? 'read_write' : 'read',
    };
    return await this.jrpc().transaction.new_trans(params);
  }
}
