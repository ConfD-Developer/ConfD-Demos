import { isValueUnset, resolveNested } from '../CommonUtils';
import { UNSET_DROPDOWN } from '../TreeNodeUtils';
import { TasksBase } from './TasksBase';

export default class TasksData extends TasksBase {
  async createPath(keypath: string): Promise<any> {
    return await this.jrpc().data.create(this.th(), keypath);
  }

  async deletePath(keypath: string): Promise<any> {
    return await this.jrpc().data.delete(this.th(), keypath);
  }

  async setValue(keypath: string, value: any, isDry = false): Promise<any> {
    return await this.jrpc().dataLeaves.set_value(this.th(), keypath, value, isDry);
  }

  async setValueDry(keypath: string, value: any): Promise<any> {
    const isDeletion = isValueUnset(value);
    const response: any = isDeletion ? await this.deletePath(keypath) : await this.setValue(keypath, value, true);

    if ('result' in response['data']) {
      return true;
    }

    const propArray = ['data', 'error', 'data', 'reason'];
    return resolveNested(response, propArray);
  }

  async existsPath(keypath: string): Promise<boolean> {
    const response: any = await this.jrpc().data.exists(this.th(), keypath);
    const propArray = ['data', 'result', 'exists'];
    const doesExist = resolveNested(response, propArray);
    return doesExist === true;
  }

  async getCase(keypath: string, choiceName: string): Promise<any> {
    const response: any = await this.jrpc().data.get_case(this.th(), keypath, choiceName);
    const caseValue = resolveNested(response, ['data', 'result', 'case']);
    return caseValue || UNSET_DROPDOWN;
  }

  async getListEntriesCount(keypath: string): Promise<number> {
    const response: any = await this.jrpc().dataLists.count_list_keys(this.th(), keypath);
    const cnt = resolveNested(response, ['data', 'result', 'count']);
    return Number.parseInt(String(cnt ?? 0), 10);
  }

  async getListKeys(keypath: string, listHandle: number, chunkSize: number): Promise<any> {
    const params = {
      th: this.th(),
      keypath,
      chunkSize,
      lh: listHandle,
    };
    const response: any = await this.jrpc().dataLists.get_list_keys(params);
    return resolveNested(response, ['data', 'result']);
  }
}
