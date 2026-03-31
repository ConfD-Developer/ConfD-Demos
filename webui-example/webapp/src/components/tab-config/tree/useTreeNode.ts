import { computed, type ComputedRef, type Ref, type WritableComputedRef } from 'vue';
import { storeToRefs } from 'pinia';
import { useTransactionStore } from 'src/stores/transaction';
import { isValueUnset } from 'src/ts/CommonUtils';
import * as nc from 'src/ts/TreeNodeUtils';
import { getState } from 'src/ts/treenodes/ConfigCommons';
import { updateNode } from 'src/ts/treenodes/ConfigChanges';
import type { ConfigContext } from 'src/ts/treenodes/ConfigStateTypes';
import type { TreeNode } from 'src/ts/TreeNodeTypes';
import type { YangSchemaNode } from 'src/ts/YangSchemaTypes';

export interface UseTreeNodeProps {
  context: ConfigContext;
  node: TreeNode;
}

export interface UseTreeNodeReturn {
  value: WritableComputedRef<any>;
  isWriteTrans: Ref<boolean>;
  transHandle: Ref<number>;
  tnKeypath: ComputedRef<string>;
  tnLabel: ComputedRef<string>;
  tnSchema: ComputedRef<any>;
  tnValue: ComputedRef<any>;
  tnKind: ComputedRef<string>;
  tnModuleTypes: ComputedRef<any>;
  tnIsConfigFalse: ComputedRef<boolean>;
  tnIsMandatory: ComputedRef<boolean>;
  tnHasDefault: ComputedRef<boolean>;
  tnIsDefault: ComputedRef<boolean>;
  tnDefaultValue: ComputedRef<any>;
  tnIsOptional: ComputedRef<boolean>;
  tnIsReadOnly: ComputedRef<boolean>;
  tnIsEditable: ComputedRef<boolean>;
  tnIsTypeEmpty: ComputedRef<boolean>;
}

export function useTreeNode(props: UseTreeNodeProps): UseTreeNodeReturn {
  const txStore = useTransactionStore();
  const { isWriteTrans, transHandle } = storeToRefs(txStore);

  const value = computed({
    get() {
      return getState(props.context.state, props.node);
    },
    set(newValue: any) {
      updateNode(props.context, props.node, newValue);
    },
  });

  const tnKeypath = computed(() => nc.nodeKeypath(props.node));
  const tnLabel = computed(() => nc.nodeLabel(props.node));
  const tnSchema = computed(() => nc.nodeSchema(props.node));
  const tnValue = computed(() => nc.nodeValue(props.node));
  const tnKind = computed(() => nc.nodeKind(props.node));
  const tnModuleTypes = computed(() => nc.nodeModuleTypes(props.node));

  const tnIsConfigFalse = computed(() => {
    const isConfigFalse = tnSchema.value['config'] === false;
    const isFalseChoice = choiceIsReadonly(tnSchema.value);
    return isConfigFalse || isFalseChoice;
  });

  const tnIsMandatory = computed(() => {
    if ('mandatory' in tnSchema.value) {
      return tnSchema.value['mandatory'] === true;
    }
    return false;
  });

  const tnHasDefault = computed(() => 'default' in tnSchema.value);

  const tnDefaultValue = computed(() => tnSchema.value['default']);

  const tnIsTypeEmpty = computed(() => {
    const schemaType = tnSchema.value['type'];
    if (isValueUnset(schemaType)) return false;
    const isPrimitive = schemaType['primitive'] === true || false;
    const isEmpty = schemaType['name'] === 'empty';
    return isPrimitive && isEmpty;
  });

  const tnIsDefault = computed(() => {
    const valueNotEmpty = !isValueUnset(value.value);
    return tnHasDefault.value && valueNotEmpty && value.value === tnDefaultValue.value;
  });

  const tnIsOptional = computed(() => !(tnIsMandatory.value || tnIsTypeEmpty.value || tnHasDefault.value));

  const tnIsReadOnly = computed(() => {
    const missingTrans = transHandle.value === -1;
    const isReadTrans = !isWriteTrans.value;
    const isConfigFalse = tnIsConfigFalse.value;
    const isReadOnly = tnSchema.value['readonly'] === true;
    return [missingTrans, isReadTrans, isConfigFalse, isReadOnly].some(Boolean);
  });

  const tnIsEditable = computed(() => {
    if (tnIsReadOnly.value) return false;

    const isChoice = tnKind.value === 'choice';
    const isEditableChoice = isChoice && !choiceIsReadonly(tnSchema.value);
    if (isEditableChoice) return true;

    const accessNode = tnSchema.value['access'];
    if (isValueUnset(accessNode)) return false;
    const hasSomeEditRights = ['create', 'update', 'delete'].some((prop) => accessNode[prop] === true);
    return hasSomeEditRights;
  });

  return {
    value,
    isWriteTrans,
    transHandle,
    tnKeypath,
    tnLabel,
    tnSchema,
    tnValue,
    tnKind,
    tnModuleTypes,
    tnIsConfigFalse,
    tnIsMandatory,
    tnHasDefault,
    tnIsDefault,
    tnDefaultValue,
    tnIsOptional,
    tnIsReadOnly,
    tnIsEditable,
    tnIsTypeEmpty,
  };
}

function choiceIsReadonly(schema: YangSchemaNode): boolean {
  const kind = nc.nodeKind(schema);
  if (kind !== 'choice') return false;
  const caseNodes = schema['cases'] ?? [];
  const roOnlyChildren = caseNodes.every((node: YangSchemaNode) =>
    (node['children'] ?? []).every((child: YangSchemaNode) => child['readonly'] === true),
  );
  return roOnlyChildren;
}
