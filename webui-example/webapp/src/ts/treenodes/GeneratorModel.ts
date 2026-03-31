import { cloneSansChildren } from '../CommonUtils';
import { newTreeNode, setNodeChildren } from '../TreeNodeUtils';
import type { YangSchemaNode } from '../YangSchemaTypes';
import type { TreeNode } from '../TreeNodeTypes';

export function generateModelNodes(moduleName: string, schema: YangSchemaNode): TreeNode[] {
  const rootNode = newTreeNode({
    key: `module/${moduleName}`,
    label: moduleName,
    type: 'root',
  });
  const childrenSchema = schema['children'];
  if (childrenSchema && childrenSchema.length > 0) {
    const childrenNodes = genModuleChildren(childrenSchema);
    setNodeChildren(rootNode, childrenNodes);
  }
  return [rootNode];
}

function genModuleChildren(childrenSchema: YangSchemaNode[]) {
  const result: any[] = [];
  for (const node of childrenSchema) {
    const childNode = genTreeNode(node, '');
    result.push(childNode);
  }
  return result;
}

function genTreeNode(jrpcNode: YangSchemaNode, parentKey: string): TreeNode {
  const nodeKeyStr = parentKey + '/' + jrpcNode['qname'];
  const nodeLabel = jrpcNode['name'];
  const nodeLevelSchema = cloneSansChildren(jrpcNode);
  const result = newTreeNode({
    key: nodeKeyStr,
    label: nodeLabel,
    type: 'default',
    schema: nodeLevelSchema,
  });
  let recursiveProp: string | null = null;
  if ('children' in jrpcNode) {
    recursiveProp = 'children';
  } else if ('cases' in jrpcNode) {
    recursiveProp = 'cases';
  }
  if (recursiveProp) {
    const childrenNodes: TreeNode[] = [];
    const nestedNode = jrpcNode[recursiveProp];
    for (const i in nestedNode) {
      const childResult = genTreeNode(nestedNode[i], nodeKeyStr);
      childrenNodes.push(childResult);
    }
    setNodeChildren(result, childrenNodes);
  }
  return result;
}
