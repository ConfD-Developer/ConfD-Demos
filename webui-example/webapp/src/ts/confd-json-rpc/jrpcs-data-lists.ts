import JrpcsBase from './jrpcs-base';

export default class JrpcsDataLists extends JrpcsBase {
  count_list_keys(th: number, keypath: string) {
    return this.basePostThPath('count_list_keys', th, keypath);
  }

  get_list_keys({
    th,
    keypath,
    chunkSize = 10,
    startWith = null,
    lh = -1,
  }: {
    th: number;
    keypath: string;
    chunkSize?: number;
    startWith?: string | null;
    lh?: number;
  }) {
    const params = {
      th: th,
      path: keypath,
      chunk_size: chunkSize,
      lh: lh,
    };
    if (startWith !== null && startWith !== undefined) {
      params['start_with'] = startWith;
    }
    return this.basePost('get_list_keys', params);
  }
}
