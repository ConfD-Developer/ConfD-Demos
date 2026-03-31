import JrpcsBase from './jrpcs-base';

export default class JrpcsDatabase extends JrpcsBase {
  lock_db(targetDb: string) {
    const params = { db: targetDb };
    return this.basePost('lock_db', params);
  }

  unlock_db(targetDb: string) {
    const params = { db: targetDb };
    return this.basePost('unlock_db', params);
  }

  copy_running_to_startup_db() {
    return this.basePostNoParams('copy_running_to_startup_db');
  }
}
