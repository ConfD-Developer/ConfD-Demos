import { useTransactionStore } from 'src/stores/transaction';
import { useServerStore } from 'src/stores/server';
import type ConfdJrpcDispatcher from '../confd-json-rpc/confd-jrpc-dispatcher';

export class TasksBase {
  jrpc(): ConfdJrpcDispatcher {
    const serverStore = useServerStore();
    if (!serverStore.dispatcher) throw new Error('Missing JRPC dispatcher!');
    return serverStore.dispatcher;
  }

  th(): number {
    const transactionStore = useTransactionStore();
    return transactionStore.transHandle;
  }
}
