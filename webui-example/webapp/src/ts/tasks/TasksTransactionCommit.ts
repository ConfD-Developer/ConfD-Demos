import { resolveNested } from '../CommonUtils';
import { TasksBase } from './TasksBase';

export default class TasksTransactionCommit extends TasksBase {
  async validateCommit(): Promise<void> {
    const response: any = await this.jrpc().transactionCommit.validate_commit(this.th());
    const propArray = ['data', 'error', 'data', 'errors'];
    const validationErrors = resolveNested(response, propArray);
    if (validationErrors) {
      throw validationErrors;
    }
  }

  async commit(): Promise<any> {
    return await this.jrpc().transactionCommit.commit(this.th());
  }
}
