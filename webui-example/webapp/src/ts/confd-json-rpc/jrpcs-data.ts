import JrpcsBase from './jrpcs-base';

export default class JrpcsData extends JrpcsBase {
  create(th: number, keypath: string) {
    return this.basePostThPath('create', th, keypath);
  }

  delete(th: number, keypath: string) {
    return this.basePostThPath('delete', th, keypath);
  }

  exists(th: number, keypath: string) {
    return this.basePostThPath('exists', th, keypath);
  }

  get_case(th: number, keypath: string, choice: string) {
    const params = {
      th: th,
      path: keypath,
      choice: choice,
    };
    return this.basePost('get_case', params);
  }
}
