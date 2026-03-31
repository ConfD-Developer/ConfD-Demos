import JrpcsBase from './jrpcs-base';

export default class JrpcsTransaction extends JrpcsBase {
  new_trans(params) {
    return this.basePost('new_trans', params);
  }

  delete_trans(th: number) {
    return this.basePostThOnly('delete_trans', th);
  }
}
