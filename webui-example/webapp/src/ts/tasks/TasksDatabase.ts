import { resolveNested } from '../CommonUtils';
import { TasksBase } from './TasksBase';

export default class TasksDatabase extends TasksBase {
  async setLockState(targetDb: string, locked: boolean): Promise<void> {
    const response: any = await this.setDbLock(targetDb, locked);
    const data = response['data'];
    if ('error' in data) {
      const message = String(resolveNested(data, ['error', 'message']) ?? 'Database lock operation failed');
      const sessions = resolveNested(data, ['error', 'data', 'sessions']);
      const error = new Error(message) as Error & { sessions?: any };
      error.sessions = sessions;
      throw error;
    }
  }

  async setDbLock(targetDb: string, boolLockValue: boolean): Promise<any> {
    const handler = this.jrpc().database;
    if (boolLockValue === true) {
      return await handler.lock_db(targetDb);
    }
    return await handler.unlock_db(targetDb);
  }
}
