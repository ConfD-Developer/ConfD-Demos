import axios from 'axios';
import { useResponsesStore } from 'src/stores/responses';
import { useErrorsStore } from 'src/stores/errors';
import { resolveNested } from '../CommonUtils';

const ENABLE_CORS = true;

export default class ConfdJrpcClient {
  axios: any;
  url: string;
  currId: number;

  constructor(baseURL: string) {
    this.axios = axios.create();
    setupHeaders(this.axios);
    setupInterceptors(this.axios);
    this.axios.defaults.baseURL = baseURL;
    this.url = '/jsonrpc';
    this.currId = 1;
  }

  // attach cookie to AXIOS instance for subsequent session requests
  setCookie(cookie: string) {
    this.axios.defaults.headers.Cookie = cookie;
  }

  getCookie() {
    return this.axios.defaults.headers.Cookie;
  }

  post(method: string, params: any) {
    const pp = buildPostParams(this.currId++, method, params);
    return this.axios.post('' + this.url + pp.path, pp.params);
  }
}

function setupHeaders(axiosInstance: any) {
  const axiosPostHeaders = axiosInstance.defaults.headers.post;
  Object.assign(axiosPostHeaders, {
    'Content-Type': 'application/json',
  });
  if (ENABLE_CORS) {
    const corsOptions = {
      crossDomain: true,
      xhrFields: { withCredentials: true },
      dataType: 'json',
    };
    Object.assign(axiosPostHeaders, corsOptions);
  }
}

function setupInterceptors(axiosInstance: any) {
  axiosInstance.interceptors.response.use(
    (response: any) => {
      const responsesStore = useResponsesStore();
      responsesStore.add(response);
      const responseError = resolveNested(response, ['data', 'error']);
      if (responseError) {
        handleError(response['data']);
      }
      return response;
    },
    (error: any) => {
      const responsesStore = useResponsesStore();
      responsesStore.add(error);
      handleError(error);
      return Promise.reject(toError(error));
    },
  );
}

function toError(error: unknown): Error {
  if (error instanceof Error) {
    return error;
  }
  if (typeof error === 'string') {
    return new Error(error);
  }
  try {
    return new Error(JSON.stringify(error));
  } catch {
    return new Error('Request failed');
  }
}

function buildPostParams(currId: number, myMethod: string, myParams: any) {
  const postParams: any = {
    jsonrpc: '2.0',
    id: currId,
    method: myMethod,
  };
  if (myParams) {
    postParams['params'] = cloneWithoutEmpties(myParams);
  }
  return {
    path: '/' + paramsToString(myMethod, postParams['params']),
    params: postParams,
  };
}

function paramsToString(method: string, myParams: any) {
  const paramsString = myParams ? JSON.stringify(myParams) : '';
  return `${method}/${paramsString}`;
}

function handleError(error: any) {
  const errorsStore = useErrorsStore();
  errorsStore.add(error);
  const errType = resolveNested(error, ['error', 'type']);
  const isSessionError = errType === 'session.invalid_sessionid';
  if (isSessionError) {
    errorsStore.addActive('ConfD session no longer valid!');
  }
}

function cloneWithoutEmpties(source: any) {
  const result: any = {};
  for (const prop in source) {
    if (source[prop] !== null && source[prop] !== undefined) {
      result[prop] = source[prop];
    }
  }
  return result;
}
