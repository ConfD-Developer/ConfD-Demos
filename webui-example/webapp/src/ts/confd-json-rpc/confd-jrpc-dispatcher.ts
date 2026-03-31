import ConfdJrpcClient from './confd-jrpc-client';

import JrpcsData from './jrpcs-data';
import JrpcsDatabase from './jrpcs-database';
import JrpcsDataLeaves from './jrpcs-data-leaves';
import JrpcsDataLists from './jrpcs-data-lists';
import JrpcsGeneral from './jrpcs-general';
import JrpcsSchema from './jrpcs-schema';
import JrpcsSession from './jrpcs-session';
import JrpcsTransaction from './jrpcs-transaction';
import JrpcsTransactionChanges from './jrpcs-transaction-changes';
import JrpcsTransactionCommit from './jrpcs-transaction-commit';

export default class ConfdJrpcDispatcher {
  client: ConfdJrpcClient;
  data: JrpcsData;
  database: JrpcsDatabase;
  dataLeaves: JrpcsDataLeaves;
  dataLists: JrpcsDataLists;
  general: JrpcsGeneral;
  schema: JrpcsSchema;
  session: JrpcsSession;
  transaction: JrpcsTransaction;
  transactionChanges: JrpcsTransactionChanges;
  transactionCommit: JrpcsTransactionCommit;

  constructor(baseURL: string) {
    const client = new ConfdJrpcClient(baseURL);
    this.client = client;

    this.data = new JrpcsData(client);
    this.database = new JrpcsDatabase(client);
    this.dataLeaves = new JrpcsDataLeaves(client);
    this.dataLists = new JrpcsDataLists(client);
    this.general = new JrpcsGeneral(client);
    this.schema = new JrpcsSchema(client);
    this.session = new JrpcsSession(client);
    this.transaction = new JrpcsTransaction(client);
    this.transactionChanges = new JrpcsTransactionChanges(client);
    this.transactionCommit = new JrpcsTransactionCommit(client);
  }

  // allow explicit cookie setting for Jest / test execution use-case
  setCookie(cookie: string) {
    this.client.setCookie(cookie);
  }

  getCookie() {
    return this.client.getCookie();
  }
}
