import JrpcsBase from './jrpcs-base';

export default class JrpcsGeneral extends JrpcsBase {
  get_system_settings(operation: string) {
    const params = { operation: operation };
    return this.basePost('get_system_setting', params);
  }
}
