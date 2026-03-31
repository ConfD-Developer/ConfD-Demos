import { newTreeNode, setNodeChildren } from '../TreeNodeUtils';

export function generateTypeNodes(moduleName: string, moduleTypesSchema: any) {
  const rootNode = newTreeNode({
    key: `types/${moduleName}`,
    label: moduleName,
    type: 'root',
    schema: moduleTypesSchema,
  });
  const namespaceNodes = genNamespaceNodes(moduleTypesSchema);
  setNodeChildren(rootNode, namespaceNodes);
  return [rootNode];
}

function genNamespaceNodes(moduleTypesSchema: any) {
  const helperMap: Record<string, any> = {};
  for (const prop in moduleTypesSchema) {
    const [namespace, typeName] = splitNamespaceTypeName(prop);
    if (!('namespace' in helperMap)) {
      helperMap[namespace] = {};
    }
    helperMap[namespace][typeName] = moduleTypesSchema[prop];
  }
  const namespaceNodes: any[] = [];
  for (const nsName in helperMap) {
    const node = newTreeNode({ key: nsName, label: nsName, type: 'namespace' });
    const typeNodesOfNamespace = genTypeNodes(nsName, helperMap[nsName]);
    setNodeChildren(node, typeNodesOfNamespace);
    namespaceNodes.push(node);
  }
  return namespaceNodes;
}

function splitNamespaceTypeName(jointName: string): [string, string] {
  const lastSemiIndex = jointName.lastIndexOf(':');
  const namespace = jointName.substring(0, lastSemiIndex);
  const name = jointName.substring(lastSemiIndex + 1);
  return [namespace, name];
}

function genTypeNodes(namespace: string, types: any) {
  const result: any[] = [];
  for (const typeName in types) {
    const typeNode = newTreeNode({
      key: `${namespace}/${typeName}`,
      label: typeName,
      type: 'type',
      schema: types[typeName],
    });
    result.push(typeNode);
  }
  return result;
}
