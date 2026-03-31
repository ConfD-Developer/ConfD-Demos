import { UNSET_DROPDOWN } from './TreeNodeUtils';
import type { YangSchemaNode } from './YangSchemaTypes';

export const T_STRING = 1;
export const T_BOOL = 2;
export const T_ENUM = 3;
export const T_NUMBER = 4;

function getTypeNode(leafSchema: YangSchemaNode) {
  return leafSchema['type'];
}

function getTypeChain(leafSchema: YangSchemaNode, moduleTypes: any) {
  const { namespace, name } = getTypeNode(leafSchema);
  const chainTypeName = `${namespace}:${name}`;
  return moduleTypes[chainTypeName];
}

export function isLeafEnum(leafSchema: YangSchemaNode, moduleTypes: any) {
  const typeSchema = getTypeNode(leafSchema);
  if ('enumeration' in typeSchema) {
    return true;
  }
  const typeChain = getTypeChain(leafSchema, moduleTypes);
  return typeChain ? typeChain.some((subType: any) => 'enumeration' in subType) : false;
}

export function isTypeUnion(leafSchema: YangSchemaNode, moduleTypes: any) {
  const typeSchema = getTypeNode(leafSchema);
  if ('primitive' in typeSchema) {
    return false;
  }
  const typeChain = getTypeChain(leafSchema, moduleTypes);
  return typeChain ? typeChain.some((subType: any) => 'union' in subType) : false;
}

export function enumOptionsFromSchema(leafSchema: YangSchemaNode, moduleTypes: any) {
  const result = [] as string[];
  const hasDefault = 'default' in leafSchema;
  const isMandatory = leafSchema['mandatory'] === true;
  if (!hasDefault && !isMandatory) {
    result.push(UNSET_DROPDOWN);
  }
  const typeChain = getTypeChain(leafSchema, moduleTypes);
  const schema = typeChain[0];
  const enumsArray = schema['enumeration'];
  for (const enumNode of enumsArray) {
    result.push(enumNode['label']);
  }
  return result;
}

export function getComponentByType({ leafSchema, moduleTypesSchema, componentMap }: any) {
  const primType = getPrimitiveType(leafSchema, moduleTypesSchema);
  let result: any = null;
  if (primType in internalMap) {
    const internalType = (internalMap as any)[primType];
    result = componentMap[internalType];
  }
  return result;
}

function getPrimitiveType(leafSchema: YangSchemaNode, moduleTypesSchema: any) {
  const typeSchema = getTypeNode(leafSchema);
  const typeChain = getTypeChain(leafSchema, moduleTypesSchema);
  if ('primitive' in typeSchema) {
    return typeSchema['name'];
  } else if (isTypeUnion(leafSchema, moduleTypesSchema)) {
    return 'string';
  }
  let result: any = null;
  for (const subType of typeChain) {
    if ('enumeration' in subType) {
      result = 'enumeration';
      break;
    }
    if ('primitive' in subType) {
      result = subType['name'];
      break;
    }
  }
  if (result === null) {
    result = typeChain[typeChain.length - 1]['name'];
  }
  return result;
}

const internalMap: Record<string, number> = {
  enumeration: T_ENUM,
  duration: T_STRING,
  string: T_STRING,
  boolean: T_BOOL,
  passwdStr: T_STRING,
  cryptHash: T_STRING,
  empty: T_BOOL,
  binary: T_BOOL,
  bits: T_STRING,
  'date-and-time': T_STRING,
  'instance-identifier': T_STRING,
  int64: T_NUMBER,
  int32: T_NUMBER,
  int16: T_NUMBER,
  uint64: T_NUMBER,
  uint32: T_NUMBER,
  uint16: T_NUMBER,
  uint8: T_NUMBER,
  'ip-prefix': T_STRING,
  'ipv4-prefix': T_STRING,
  'ipv6-prefix': T_STRING,
  'ip-address-and-prefix-length': T_STRING,
  'ipv4-address-and-prefix-length': T_STRING,
  'ipv6-address-and-prefix-length': T_STRING,
  'hex-string': T_STRING,
  'dotted-quad': T_STRING,
  'ip-address': T_STRING,
  'ipv4-address': T_STRING,
  'ipv6-address': T_STRING,
  gauge32: T_NUMBER,
  counter32: T_NUMBER,
  counter64: T_NUMBER,
  'object-identifier': T_STRING,
};
