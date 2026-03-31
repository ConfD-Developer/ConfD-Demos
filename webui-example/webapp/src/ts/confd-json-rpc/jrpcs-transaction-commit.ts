import JrpcsBase from './jrpcs-base';

export default class JrpcsTransactionCommit extends JrpcsBase {
  validate_commit(th: number) {
    return this.basePostThOnly('validate_commit', th);
  }

  clear_validate_lock(th: number) {
    return this.basePostThOnly('clear_validate_lock', th);
  }

  commit(th: number) {
    return this.basePostThOnly('commit', th);
  }
}
