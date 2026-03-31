import { createPinia, setActivePinia } from 'pinia';
import { afterAll, beforeAll, beforeEach, expect, test } from 'vitest';
import { useServerStore } from 'src/stores/server';
import ConfdJrpcDispatcher from '../confd-jrpc-dispatcher';

const SINGLE_TEST_TIMEOUT_MS = 5000;

let dispatcher: any = null;

function hasOwn(obj: unknown, prop: string): boolean {
  return Object.prototype.hasOwnProperty.call(obj, prop);
}

function isJrpcResponseOk(response: any): boolean {
  const isStatusOk = response?.['statusText'] === 'OK';
  const hasSomeError = hasOwn(response?.['data'], 'error');
  return isStatusOk && !hasSomeError;
}

const jrpcGetLoggedInDispatcher = async () => {
  setActivePinia(createPinia());
  const serverStore = useServerStore();
  const host = 'http://localhost:8008';
  const { user, password } = serverStore.loginInfo;
  const result = new ConfdJrpcDispatcher(host);
  const response = await result.session.login(user, password);
  expect(isJrpcResponseOk(response)).toBeTruthy();
  const [cookie] = response['headers']['set-cookie'] || [null];
  expect(cookie).toBeTruthy();
  result.setCookie(cookie);
  return result;
};

beforeAll(async () => {
  dispatcher = await jrpcGetLoggedInDispatcher();
});

afterAll(async () => {
  if (dispatcher) {
    await dispatcher.session.logout();
  }
});

beforeEach(() => {
  expect.hasAssertions();
});

test('ConfD login', () => {
  const sessionCookie = dispatcher.getCookie();
  expect(sessionCookie).toEqual(expect.any(String));
});

const jrpcGetModelsList = async () => {
  const response = await dispatcher.general.get_system_settings('models');
  expect(isJrpcResponseOk(response)).toBeTruthy();
  const models = response.data.result || null;
  expect(Array.isArray(models)).toBeTruthy();
  expect(models.length).toBeGreaterThan(0);
  return models;
};

test('get_system_settings - models', async () => {
  const models = await jrpcGetModelsList();
  models.forEach((model: any) => {
    expect(model).toMatchObject({
      prefix: expect.any(String),
      namespace: expect.any(String),
      name: expect.any(String),
    });
  });
});

const jrpcGetReadTransHandle = async () => {
  const handler = dispatcher.transaction;
  const params = {
    db: 'running',
    mode: 'read',
  };
  const response = await handler.new_trans(params);
  expect(isJrpcResponseOk(response)).toBeTruthy();
  const handle = response.data.result.th || null;
  expect(handle).toBeTruthy();
  return handle;
};

const jrpcCloseTransHandle = async (th: number) => {
  const response = await dispatcher.transaction.delete_trans(th);
  expect(isJrpcResponseOk(response)).toBeTruthy();
};

test('new_trans, delete_trans - read/running', async () => {
  const handle = await jrpcGetReadTransHandle();
  expect(handle).toBeGreaterThan(0);
  await jrpcCloseTransHandle(handle);
});

const jrpcGetFullSchema = async (th: number, namespace: string) => {
  expect(th).toEqual(expect.any(Number));
  expect(namespace).toEqual(expect.any(String));
  const response = await dispatcher.schema.getSchemaByNamespace(th, namespace);
  expect(isJrpcResponseOk(response)).toBeTruthy();
  const schema = response.data.result || null;
  expect(schema).toBeTruthy();
  return schema;
};

const jrpcGetLevelSchema = async (th: number, keypath: string) => {
  expect(th).toEqual(expect.any(Number));
  expect(keypath).toEqual(expect.any(String));
  const response = await dispatcher.schema.getLevelSchema(th, keypath);
  expect(isJrpcResponseOk(response)).toBeTruthy();
  const schema = response.data.result || null;
  expect(schema).toBeTruthy();
  return schema;
};

test(
  'get_schema - full for each model',
  async () => {
    const models = await jrpcGetModelsList();
    const handle = await jrpcGetReadTransHandle();

    const namespaces = models.map((model: any) => model.namespace);
    expect(Array.isArray(namespaces)).toBeTruthy();
    expect(namespaces.length).toBeGreaterThan(0);

    const promises: Promise<any>[] = [];
    namespaces.forEach((namespace: string) => {
      const schemaPromise = jrpcGetFullSchema(handle, namespace);
      promises.push(schemaPromise);
    });

    const responses = await Promise.all(promises);
    expect(Array.isArray(responses)).toBeTruthy();
    expect(responses.length).toEqual(namespaces.length);
  },
  SINGLE_TEST_TIMEOUT_MS,
);

function isSchemaDataValid(schema: any): boolean {
  const requiredFields = ['kind', 'name', 'qname'];
  requiredFields.forEach((field) => {
    expect(hasOwn(schema, field)).toBeTruthy();
  });

  const recursiveProperties = ['children', 'cases'];
  recursiveProperties.forEach((prop) => {
    if (hasOwn(schema, prop)) {
      return schema[prop].every(isSchemaDataValid);
    }
  });

  return true;
}

test('get_schema - single level, with values', async () => {
  const handle = await jrpcGetReadTransHandle();
  const keypath = '/r:sys';
  const schema = await jrpcGetLevelSchema(handle, keypath);
  expect(isSchemaDataValid(schema.data)).toBeTruthy();
});

const jrpcDataExists = async (th: number, keypath: string) => {
  expect(th).toEqual(expect.any(Number));
  expect(keypath).toEqual(expect.any(String));
  const response = await dispatcher.data.exists(th, keypath);
  expect(isJrpcResponseOk(response)).toBeTruthy();
  const doesExist = response.data.result.exists || null;
  expect(doesExist).toEqual(expect.any(Boolean));
  return doesExist;
};

test('get_data - exists', async () => {
  const handle = await jrpcGetReadTransHandle();
  const keypath = '/r:sys/r:routes';
  const doesExist = await jrpcDataExists(handle, keypath);
  expect(doesExist).toBeTruthy();
});

const jrpcDataListCount = async (th: number, keypath: string) => {
  expect(th).toEqual(expect.any(Number));
  expect(keypath).toEqual(expect.any(String));
  const response = await dispatcher.dataLists.count_list_keys(th, keypath);
  expect(isJrpcResponseOk(response)).toBeTruthy();
  const count = response.data.result.count || null;
  expect(count).toEqual(expect.any(Number));
  return count;
};

test('count_list_keys', async () => {
  const handle = await jrpcGetReadTransHandle();
  const keypath = '/r:sys/r:routes/r:inet/r:route';
  const entryCount = await jrpcDataListCount(handle, keypath);
  expect(entryCount).toEqual(8);
});

const jrpcDataListKeys = async (th: number, keypath: string, lh: number) => {
  expect(th).toEqual(expect.any(Number));
  expect(keypath).toEqual(expect.any(String));
  const CHUNK_SIZE = 5;

  const params = {
    th,
    keypath,
    chunkSize: CHUNK_SIZE,
    lh,
  };
  const response = await dispatcher.dataLists.get_list_keys(params);
  expect(isJrpcResponseOk(response)).toBeTruthy();

  const entriesArr = response.data.result.keys || null;
  expect(Array.isArray(entriesArr)).toBeTruthy();
  expect(entriesArr.length).toBeGreaterThanOrEqual(0);
  expect(entriesArr.length).toBeLessThanOrEqual(CHUNK_SIZE);

  return entriesArr;
};

test('get_list_keys', async () => {
  const handle = await jrpcGetReadTransHandle();
  const keypath = '/r:sys/r:routes/r:inet/r:route';
  const lh = -1;
  const listEntries = await jrpcDataListKeys(handle, keypath, lh);
  expect(listEntries.length).toBeGreaterThan(0);
  listEntries.forEach((entry: any[]) => {
    expect(Array.isArray(entry)).toBeTruthy();
    expect(entry.length).toBeGreaterThan(0);
  });
});

test('get_schema - list entry', async () => {
  const handle = await jrpcGetReadTransHandle();
  const keypath = '/r:sys/r:routes/r:inet/r:route{"10.0.0.0" "24"}';
  const schema = await jrpcGetLevelSchema(handle, keypath);
  expect(isSchemaDataValid(schema.data)).toBeTruthy();
});

const jrpcGetValue = async (th: number, keypath: string) => {
  expect(th).toEqual(expect.any(Number));
  expect(keypath).toEqual(expect.any(String));

  const response = await dispatcher.dataLeaves.get_value(th, keypath);
  expect(isJrpcResponseOk(response)).toBeTruthy();

  const value = response.data.result.value || null;
  expect(value).toBeTruthy();
  return value;
};

test('get_value', async () => {
  const keypath = '/r:sys/r:routes/r:inet/r:route{"10.0.0.0" "24"}/';
  const handle = await jrpcGetReadTransHandle();

  let value: any = null;

  value = await jrpcGetValue(handle, keypath + '/r:prefix-length');
  expect(value).toEqual('24');

  value = await jrpcGetValue(handle, keypath + '/r:enabled');
  expect(value).toEqual('true');
});
