// base class for all JSON-RPC groups of methods;

import type ConfdJrpcClient from './confd-jrpc-client';

// promise-ified post methods below to be used by descendants of this class
export default class JrpcsBase {
  client: ConfdJrpcClient;

  constructor(jsonRpcClient: ConfdJrpcClient) {
    this.client = jsonRpcClient;
  }

  basePost(method: string, params: any) {
    return this.client.post(method, params);
  }

  basePostNoParams(method: string) {
    return this.basePost(method, null);
  }

  basePostThOnly(method: string, th: number) {
    const params = { th: th };
    return this.basePost(method, params);
  }

  basePostThPath(method: string, th: number, keypath: string) {
    const params = { th: th, path: keypath };
    return this.basePost(method, params);
  }
}
