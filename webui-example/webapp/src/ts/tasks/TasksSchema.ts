import { resolveNested } from '../CommonUtils'
import { TasksBase } from './TasksBase'

export default class TasksSchema extends TasksBase {
  async getLevelSchema(keypath: string): Promise<any> {
    const response: any = await this.jrpc().schema.getLevelSchema(this.th(), keypath)
    return resolveNested(response, ['data', 'result', 'data'])
  }
}
