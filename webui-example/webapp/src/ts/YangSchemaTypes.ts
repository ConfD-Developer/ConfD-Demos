// TODO - this is loose DIY definition of ConfD's JSON-RPC schema,
// check official docs for official structure if applicable...
export interface YangSchemaNode {
  name?: string;
  qname?: string;
  kind?: string;
  children?: YangSchemaNode[];
  cases?: YangSchemaNode[];
  [key: string]: any;
}

export interface YangModuleSchema {
  data: YangSchemaNode;
  [key: string]: any;
}
