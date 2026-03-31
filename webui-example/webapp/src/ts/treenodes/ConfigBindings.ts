import { isValueUnset } from '../CommonUtils';
import { isLeafEnum } from '../TypeExtractor';
import {
  nodeKey,
  nodeKeypath,
  nodeSchema,
  nodeValue,
  UNSET_DROPDOWN,
  nodeKind,
  nodeModuleTypes,
} from '../TreeNodeUtils';
import { splitChoiceKeypath } from './ConfigCommons';
import type { ConfigContext, ConfigState, ListMeta } from './ConfigStateTypes';
import type { TreeNode } from '../TreeNodeTypes';

export function bindData(context: ConfigContext, nodeArray: TreeNode[]) {
  for (const node of nodeArray) {
    bindNode(context, node);
  }
}

type Binder = (context: ConfigContext, node: TreeNode) => void | Promise<void>;

function bindNode(context: ConfigContext, node: TreeNode) {
  const binder: Binder | undefined = {
    leaf: bindLeaf,
    container: bindPresenceContainer,
    choice: bindChoice,
    'leaf-list': bindLeafList,
    list: bindList,
  }[nodeKind(node)];
  if (binder) {
    void binder(context, node);
  }
}

function bindLeaf({ state }: ConfigContext, node: TreeNode) {
  const schema = nodeSchema(node);
  let value: any = null;
  if ('value' in schema) {
    value = schema['value'];
  } else if ('default' in schema) {
    value = schema['default'];
  }
  const isEnum = isLeafEnum(schema, nodeModuleTypes(node));
  if (isEnum && isValueUnset(value)) {
    value = UNSET_DROPDOWN;
  }
  const key = nodeKey(node);
  state[key] = value;
}

function bindPresenceContainer({ tasker, state }: ConfigContext, node: TreeNode) {
  void (async () => {
    const keypath = nodeKeypath(node);
    const doesExist: boolean = await tasker.data.existsPath(keypath);
    const key = nodeKey(node);
    state[key] = doesExist;
    if (!doesExist) {
      delete node.lazy;
    }
  })();
}

async function bindChoice({ tasker, state }: ConfigContext, node: TreeNode) {
  const dirtyKeypath = nodeKeypath(node);
  const [keypath, choiceName] = splitChoiceKeypath(dirtyKeypath);
  const response: any = await tasker.data.getCase(keypath, choiceName);
  const key = nodeKey(node);
  state[key] = response;
  if (response === UNSET_DROPDOWN) {
    node.lazy = false;
  }
}

export function initListData(state: ConfigState, node: TreeNode) {
  const chunkSize = 10;
  const listData: ListMeta = {
    total: 0,
    position: -chunkSize,
    chunk_size: chunkSize,
    lh: -1,
  };
  const key = nodeKey(node);
  state[key] = listData;
}

function bindList({ state, tasker }: ConfigContext, node: TreeNode) {
  initListData(state, node);
  void (async () => {
    const keypath = nodeKeypath(node);
    const count: number = await tasker.data.getListEntriesCount(keypath);
    const key = nodeKey(node);
    (state[key] as ListMeta).total = count;
  })();
}

function bindLeafList({ state }: ConfigContext, node: TreeNode) {
  const key = nodeKey(node);
  const valueArr = nodeValue(node);
  state[key] = valueArr;
}
