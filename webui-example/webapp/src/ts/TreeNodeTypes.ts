import type { QTreeNode } from 'quasar';
import type { YangSchemaNode } from './YangSchemaTypes';

export interface TreeNode extends QTreeNode {
  'tree-id'?: string;
  'module-types'?: Record<string, any>;
  schema?: YangSchemaNode;
  children?: TreeNode[];
}
