import type TaskHandler from '../tasks/TaskHandler';
import { nodeKey, nodeKeypath, setNodeSchema } from '../TreeNodeUtils';
import type { ConfigState, ConfigStateEntry } from './ConfigStateTypes';
import type { TreeNode } from '../TreeNodeTypes';
import type { YangSchemaNode } from '../YangSchemaTypes';

export function getState(state: ConfigState, node: TreeNode): ConfigStateEntry | undefined {
  const key = nodeKey(node);
  return state[key];
}

export async function loadListEntrySchemaPromise(tasker: TaskHandler, node: TreeNode): Promise<void> {
  const entryKp = nodeKeypath(node);
  const schemaData: YangSchemaNode = await tasker.schema.getLevelSchema(entryKp);
  setNodeSchema(node, schemaData);
}

// MAAPI case node needs separate path to choice / choice name
export function splitChoiceKeypath(dirtyKp: string): [string, string] {
  const lastSlashIndex = dirtyKp.lastIndexOf('/');
  const keypath = dirtyKp.substring(0, lastSlashIndex);
  const choiceQName = dirtyKp.substring(lastSlashIndex + 1);
  const semiIndex = choiceQName.indexOf(':');
  const choiceName = choiceQName.substring(semiIndex + 1);
  return [keypath, choiceName];
}
