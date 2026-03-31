import JrpcsBase from './jrpcs-base';

export default class JrpcsDataLeaves extends JrpcsBase {
  get_value(th: number, keypath: string, checkDefault = false) {
    const params = {
      th: th,
      path: keypath,
      check_default: checkDefault,
    };
    return this.basePost('get_value', params);
  }

  set_value(th: number, keypath: string, value: any, isDry = false) {
    const params = {
      th: th,
      path: keypath,
      value: String(value),
      dryrun: isDry,
    };
    return this.basePost('set_value', params);
  }
}
