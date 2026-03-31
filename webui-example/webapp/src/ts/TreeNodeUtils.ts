// common items related to Quasar QTree nodes generated from JSON-RPC data
import type { TreeNode } from './TreeNodeTypes';
import type { YangSchemaNode } from './YangSchemaTypes';

export const columnNameKey = () => TN_KEY;
export const columnNameLabel = () => TN_LABEL;

export function newTreeNode({ key, label, type, schema = null }: any): TreeNode {
  const node: TreeNode = {
    [TN_KEY]: key,
    [TN_LABEL]: label,
    [TN_HEADER]: type,
    [TN_BODY]: type,
    [TN_SCHEMA]: schema,
    [TN_KIND]: schema ? schema['kind'] : type,
    selectable: false,
    tickable: false,
  };
  return node;
}

export function newLazyTreeNode({ key, label, type, schema, moduleTypes }: any) {
  const node = newTreeNode({ key, label, type, schema });
  if (isLazy(type)) {
    node[TN_LAZY] = true;
  }
  node[TN_TYPES] = moduleTypes;
  return node;
}

function isLazy(type: string) {
  const lazyKinds = ['config', 'container', 'list', 'list-entry', 'choice'];
  return lazyKinds.includes(type);
}

export function setNodeChildren(node: TreeNode, children: TreeNode[]) {
  node[TN_CHILDREN] = children;
}

export const UNSET_DROPDOWN = '<< not-set >>';

export function nodeKey(node: TreeNode) {
  return String(node[TN_KEY] ?? '');
}

export function nodeValue(node: TreeNode) {
  return nodeSchema(node)['value'] || null;
}

export function nodeKeypath(node: TreeNode): string {
  const key = nodeKey(node);
  const [, keypath] = treeKeyToKeypath(key);
  return keypath;
}

function treeKeyToKeypath(key: string): [string, string] {
  const pipeIndex = key.indexOf('|');
  const namespace = key.substring(0, pipeIndex);
  const path = key.substring(pipeIndex + 1);
  return [namespace, path];
}

export function nodeLabel(node: TreeNode) {
  return String(node[TN_LABEL] ?? '');
}

export function nodeSchema(node: TreeNode) {
  return node[TN_SCHEMA] ?? {};
}

export function setNodeSchema(node: TreeNode, schema: YangSchemaNode) {
  node[TN_SCHEMA] = schema;
}

export function nodeModuleTypes(node: TreeNode) {
  return node[TN_TYPES] ?? {};
}

export function nodeKind(node: TreeNode) {
  return String(node[TN_KIND] ?? '');
}

// Quasar QTree related nodes for correct template selection
const TN_KEY = 'tree-id';
const TN_LABEL = 'name';
const TN_HEADER = 'header';
const TN_BODY = 'body';

const TN_SCHEMA = 'schema';
const TN_CHILDREN = 'children';
const TN_LAZY = 'lazy';
const TN_TYPES = 'module-types';
const TN_KIND = 'kind';
