import { resolveNested } from '../CommonUtils';
import { TasksBase } from './TasksBase';

export interface TransactionChange {
  path: string;
  label: string;
  old?: any;
  value?: any;
  op: 'created' | 'deleted' | 'modified' | 'value_set';
}

export default class TasksTransactionChanges extends TasksBase {
  async getTransChanges(): Promise<TransactionChange[]> {
    const response: any = await this.jrpc().transactionChanges.get_trans_changes(this.th());
    const propArray = ['data', 'result', 'changes'];
    return resolveNested(response, propArray);
  }

  async validateTransaction(): Promise<any> {
    const response: any = await this.jrpc().transactionChanges.validate_trans(this.th());
    const resData = response['data'];
    if ('error' in resData) {
      const propArray = ['error', 'data', 'errors'];
      throw resolveNested(resData, propArray);
    }
    return resData['warnings'];
  }
}
