import JrpcsBase from './jrpcs-base';

export default class JrpcsTransactionChanges extends JrpcsBase {
  is_trans_modified(th: number) {
    return this.basePostThOnly('is_trans_modified', th);
  }

  get_trans_changes(th: number) {
    const params = {
      th: th,
      output: 'legacy',
    };
    return this.basePost('get_trans_changes', params);
  }

  validate_trans(th: number) {
    return this.basePostThOnly('validate_trans', th);
  }
}
