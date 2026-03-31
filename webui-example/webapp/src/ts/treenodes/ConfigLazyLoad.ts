import { nodeKey, nodeKeypath, nodeKind, nodeModuleTypes, nodeSchema } from '../TreeNodeUtils';
import { getState, loadListEntrySchemaPromise } from './ConfigCommons';
import { generateLazyDescendants, generateListEntries } from './GeneratorConfig';
import type { ConfigContext, ListMeta } from './ConfigStateTypes';
import type { TreeNode } from '../TreeNodeTypes';

export function getLazyNodes(context: ConfigContext, node: TreeNode) {
  const lazyLoader = {
    choice: lazyChoice,
    list: lazyList,
  }[nodeKind(node)];
  return lazyLoader ? lazyLoader(context, node) : lazyDefault(context, node);
}

function lazyDefault({ tasker }: ConfigContext, node: TreeNode) {
  return (async () => {
    const keypath = nodeKeypath(node);
    const schemaData = await tasker.schema.getLevelSchema(keypath);
    const key = nodeKey(node);
    const moduleTypes = nodeModuleTypes(node);
    const nodes = generateLazyDescendants(key, schemaData, moduleTypes);
    return nodes;
  })();
}

function lazyChoice({ state }: ConfigContext, node: TreeNode) {
  const choiceValue = getState(state, node);
  const schema = nodeSchema(node);
  const caseNodes = schema['cases']?.filter((val: any) => val['name'] === choiceValue) ?? [];
  const key = nodeKey(node);
  const moduleTypes = nodeModuleTypes(node);
  const nodes = generateLazyDescendants(key, caseNodes[0], moduleTypes);
  return Promise.resolve(nodes);
}

function lazyList(context: ConfigContext, node: TreeNode) {
  return getListEntriesAt(context, node, -1);
}

export function getListEntriesAt({ state, tasker }: ConfigContext, listNode: TreeNode, listHandle: number) {
  return (async () => {
    const keypath = nodeKeypath(listNode);
    const listData = getState(state, listNode) as ListMeta;
    const chunkSize = listData['chunk_size'];
    const keysJson = await tasker.data.getListKeys(keypath, listHandle, chunkSize);
    const nodes = generateListEntries({ listNode, keysJson });
    await Promise.all(nodes.map((entryNode: TreeNode) => loadListEntrySchemaPromise(tasker, entryNode)));

    const responseLh = Number.isInteger(keysJson['lh']) ? keysJson['lh'] : listHandle;
    const fromStart = listHandle === -1;
    const newPosition = fromStart ? 0 : listData['position'] + chunkSize;
    listData.position = newPosition;
    listData.lh = responseLh;
    return nodes;
  })();
}
