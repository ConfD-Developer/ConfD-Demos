import JrpcsBase from './jrpcs-base';

export default class JrpcsSchema extends JrpcsBase {
  get_schema(params: any) {
    return this.basePost('get_schema', params);
  }

  // get full schema of specified namespace
  getSchemaByNamespace(th: number, namespace: string) {
    const params = {
      th: th,
      namespace: namespace,
      insert_values: false,
    };
    return this.get_schema(params);
  }

  // get single depth level of schema for specified keypath
  getLevelSchema(th: number, keypath: string) {
    const params = {
      th: th,
      path: keypath,
      levels: 1,
      insert_values: true,
    };
    return this.get_schema(params);
  }
}
