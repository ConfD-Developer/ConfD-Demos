import JrpcsBase from './jrpcs-base';

export default class JrpcsSession extends JrpcsBase {
  login(user: string, passwd: string) {
    const params = { user, passwd };
    return this.basePost('login', params);
  }

  logout() {
    return this.basePostNoParams('logout');
  }
}
