import { cloneSansChildren } from '../CommonUtils';
import { splitChoiceKeypath } from './ConfigCommons';

import {
  newLazyTreeNode,
  nodeKey,
  nodeKeypath,
  nodeKind,
  nodeModuleTypes,
  nodeSchema,
  setNodeChildren,
} from '../TreeNodeUtils';
import type { TreeNode } from '../TreeNodeTypes';
import type { YangSchemaNode } from '../YangSchemaTypes';

export function generateToplevelNode(moduleName: string, schema: YangSchemaNode) {
  const meta = schema['meta'];
  const key = meta['namespace'] + '|';
  const label = moduleName;
  const type = 'root';
  const moduleTypes = meta['types'];
  const result = newLazyTreeNode({ key, label, type, schema, moduleTypes });
  const descendants = generateLazyDescendants(key, schema['data'], moduleTypes);
  setNodeChildren(result, descendants);
  return result;
}

export function generateLazyDescendants(path: string, nodeSchemaArg: any, moduleTypes: any) {
  const result: TreeNode[] = [];
  const thisKind = nodeKind(nodeSchemaArg);
  let fixedKey = path;
  if (thisKind === 'case') {
    const [keypath] = splitChoiceKeypath(path);
    fixedKey = keypath;
  }
  for (const child of nodeSchemaArg['children']) {
    const newNodeParams = {
      key: `${fixedKey}/${child['qname']}`,
      label: child['name'],
      type: nodeKind(child),
      schema: cloneSansChildren(child),
      moduleTypes,
    };
    const node = newLazyTreeNode(newNodeParams);
    node['parent'] = path;
    result.push(node);
  }
  return result;
}

function keys2keypath(keysArray: string[], isListKeyless: boolean) {
  if (isListKeyless) {
    const pseudoKey = keysArray[0];
    return `["${pseudoKey}"]`;
  } else {
    const quotedKeys = keysArray.map((x) => `"${x}"`);
    return '{' + quotedKeys.join(' ') + '}';
  }
}

export function generateListEntries({ listNode, keysJson }: any) {
  const result: TreeNode[] = [];
  for (const keyArr of keysJson['keys']) {
    const node = generateListEntry({ listNode, keyArr });
    result.push(node);
  }
  return result;
}

function isListKeyless(listNode: TreeNode) {
  const schema = nodeSchema(listNode);
  return !('key' in schema);
}

export function generateListEntry({ listNode, keyArr }: { listNode: TreeNode; keyArr: string[] }) {
  const listKeypath = nodeKeypath(listNode);
  const parenthesedKeys = keys2keypath(keyArr, isListKeyless(listNode));
  const newNodeParams = {
    key: listKeypath + parenthesedKeys,
    label: parenthesedKeys,
    type: 'list-entry',
    schema: { kind: 'list-entry' },
    moduleTypes: nodeModuleTypes(listNode),
  };
  const node = newLazyTreeNode(newNodeParams);
  node['parent'] = nodeKey(listNode);
  return node;
}
