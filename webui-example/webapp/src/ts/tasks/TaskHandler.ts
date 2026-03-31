import TasksConfig from './TasksConfig';
import TasksData from './TasksData';
import TasksDatabase from './TasksDatabase';
import TasksModel from './TasksModel';
import TasksSession from './TasksSession';
import TasksSchema from './TasksSchema';
import TasksTransaction from './TasksTransaction';
import TasksTransactionChanges from './TasksTransactionChanges';
import TasksTransactionCommit from './TasksTransactionCommit';

// main handler for invoking the "tasks";
// - acts as a wrapper around ConfD JSON-RPC method invocation;
// - to be invoked in middleware / components as webapp architecture requires;
export default class TaskHandler {
  config: TasksConfig;
  data: TasksData;
  database: TasksDatabase;
  models: TasksModel;
  schema: TasksSchema;
  session: TasksSession;
  transaction: TasksTransaction & { changes: TasksTransactionChanges; commit: TasksTransactionCommit };

  constructor() {
    this.config = new TasksConfig();
    this.data = new TasksData();
    this.database = new TasksDatabase();
    this.models = new TasksModel();
    this.schema = new TasksSchema();
    this.session = new TasksSession();
    this.transaction = new TasksTransaction() as TaskHandler['transaction'];
    this.transaction.changes = new TasksTransactionChanges();
    this.transaction.commit = new TasksTransactionCommit();
  }
}
