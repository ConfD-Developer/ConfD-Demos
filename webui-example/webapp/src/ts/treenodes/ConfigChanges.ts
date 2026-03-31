import { isValueUnset } from '../CommonUtils';
import { nodeKey, nodeKeypath, nodeKind, nodeSchema } from '../TreeNodeUtils';
import { getState, loadListEntrySchemaPromise, splitChoiceKeypath } from './ConfigCommons';
import { initListData } from './ConfigBindings';
import { getListEntriesAt } from './ConfigLazyLoad';
import { generateListEntry } from './GeneratorConfig';
import type { ConfigContext, ListMeta } from './ConfigStateTypes';
import type { TreeNode } from '../TreeNodeTypes';

export function updateNode(context: ConfigContext, node: TreeNode, value: any) {
  const updater = {
    leaf: updateSimple,
    'leaf-list': updateSimple,
    container: updateContainer,
    choice: updateChoice,
  }[nodeKind(node)];
  if (updater) {
    updater(context, node, value);
  }
}

function updateSimple({ state, tasker }: ConfigContext, node: TreeNode, value: any) {
  const key = nodeKey(node);
  const keypath = nodeKeypath(node);
  if (isValueUnset(value)) {
    delete state[key];
    void tasker.data.deletePath(keypath);
  } else {
    state[key] = value;
    void tasker.data.setValue(keypath, value);
  }
}

function updateContainer(context: ConfigContext, node: TreeNode, value: any) {
  updateSimple(context, node, value);
  const keypath = nodeKeypath(node);
  if (value === true) {
    node.lazy = true;
    void context.tasker.data.createPath(keypath);
  } else {
    delete node.lazy;
    delete node.children;
    node.expandable = false;
    const key = nodeKey(node);
    context.tree.setExpanded(key, false);
    dropPrefixProps(context.tree['lazy'], key);
    void context.tasker.data.deletePath(keypath);
  }
}

function deleteCase({ state, tasker, tree }: ConfigContext, choiceKey: string, caseSchema: any) {
  const caseChildren = caseSchema['children'];
  for (const child of caseChildren) {
    const isNestedChoice = nodeKind(child) === 'choice';
    const [baseKp] = splitChoiceKeypath(choiceKey);
    const keypath = `${baseKp}/${child['qname']}`;
    if (isNestedChoice) {
      deleteCasesExcept({ state, tasker, tree }, child['cases'], keypath, null);
    } else {
      void tasker.data.deletePath(keypath);
    }
  }
}

function deleteCasesExcept(
  context: ConfigContext,
  casesSchemaArray: any[],
  choiceTreeKey: string,
  newCase: string | null,
) {
  for (const caseSchema of casesSchemaArray) {
    const caseName = caseSchema['name'];
    if (caseName !== newCase) {
      deleteCase(context, choiceTreeKey, caseSchema);
    }
  }
}

function updateChoice(context: ConfigContext, node: TreeNode, value: any) {
  const newCase = value;
  const choiceTreeKey = nodeKey(node);
  context.tree.setExpanded(choiceTreeKey, false);
  const choiceCases = nodeSchema(node)['cases'] ?? [];
  deleteCasesExcept(context, choiceCases, choiceTreeKey, newCase);
  if (isValueUnset(newCase)) {
    delete node.lazy;
  } else {
    node.lazy = true;
  }
  dropPrefixProps(context.tree['lazy'], choiceTreeKey);
  dropPrefixProps(context.state, choiceTreeKey);
  context.state[choiceTreeKey] = newCase;
  delete node.children;
}

function dropPrefixProps(obj: any, prefix: string) {
  if (!obj) return;
  Object.keys(obj)
    .filter((key) => prefixMatches(prefix, key))
    .map((key) => {
      delete obj[key];
    });
  delete obj[prefix];
}

function prefixMatches(prefix: string, candidate: string) {
  if (!candidate.startsWith(prefix)) {
    return false;
  }
  if (prefix.length === candidate.length) {
    return true;
  }
  return candidate[prefix.length] === '/';
}

export function deleteListEntry({ state, tasker, tree }: ConfigContext, node: TreeNode) {
  const parentKey = node['parent'];
  const parentNode = tree.getNodeByKey(parentKey);
  const key = nodeKey(node);
  const siblings = parentNode['children'].filter((el: any) => nodeKey(el) !== key);
  parentNode.children = siblings;
  const listData = getState(state, parentNode) as ListMeta;
  if (siblings.length < 1) {
    parentNode.lazy = true;
    parentNode.expanded = false;
  }
  listData.total = siblings.length;
  dropPrefixProps(state, key);
  dropPrefixProps(tree['lazy'], key);
  const keypath = nodeKeypath(node);
  void tasker.data.deletePath(keypath);
}

export function addLeafListEntry({ state }: ConfigContext, node: TreeNode, value: any) {
  let listData = getState(state, node) as any[] | undefined;
  if (isValueUnset(listData)) {
    const key = nodeKey(node);
    state[key] = [];
    listData = state[key] as any[];
  }
  (listData as any[]).push(value);
  // tasker/json-rpc already handled before this tree update
}

export function deleteLeafListEntry({ state, tasker }: ConfigContext, node: TreeNode, value: any) {
  const listData = getState(state, node) as any[];
  const pos = listData.indexOf(value);
  if (pos > -1) {
    listData.splice(pos, 1);
  }
  const leafListKp = nodeKeypath(node);
  const entryKp = `${leafListKp}{${value}}`;
  void tasker.data.deletePath(entryKp);
}

export function deleteList({ state, tasker, tree }: ConfigContext, node: TreeNode) {
  const listData = getState(state, node) as ListMeta;
  const key = nodeKey(node);
  tree.setExpanded(key, false);
  delete node.children;
  node.lazy = true;
  node.expanded = false;
  listData.total = 0;
  dropPrefixProps(state, key);
  dropPrefixProps(tree['lazy'], key);
  initListData(state, node);
  const keypath = nodeKeypath(node);
  void tasker.data.deletePath(keypath);
}

export function addListEntry({ state, tasker }: ConfigContext, listNode: TreeNode, keyArr: any[]) {
  const listEntryNode = generateListEntry({ listNode, keyArr });
  void (async () => {
    await loadListEntrySchemaPromise(tasker, listEntryNode);
    const listData = getState(state, listNode) as ListMeta;
    const total = listData['total'];
    listData.total = total + 1;
  })();
  if (!('children' in listNode)) {
    listNode.children = [];
  }
  listNode['children'].push(listEntryNode);
}

export async function getNextListEntries(context: ConfigContext, node: TreeNode, fromStart: boolean) {
  const listKey = nodeKey(node);
  const oldChildren = node['children'] ?? [];
  const listData = getState(context.state, node) as ListMeta;
  const listHandle = fromStart ? -1 : listData['lh'];
  const nodes = await getListEntriesAt(context, node, listHandle);

  for (const child of oldChildren) {
    const childKey = nodeKey(child);
    dropPrefixProps(context.state, childKey);
    dropPrefixProps(context.tree['lazy'], childKey);
  }

  node.children = nodes;
  node.expanded = true;
  context.tree.setExpanded(listKey, true);
}
