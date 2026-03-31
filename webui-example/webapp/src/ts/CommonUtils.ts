import { UNSET_DROPDOWN } from './TreeNodeUtils';

export function cloneSansChildren(obj: any) {
  return cloneSansProps(obj, ['children']);
}

export function stringifySansChildren(json: any) {
  return JSON.stringify(json, stringifyFilter, 2);
}

function cloneSansProps(obj: any, removePropsArr: string[]) {
  const result: any = {};
  for (const prop in obj) {
    if (!removePropsArr.includes(prop)) {
      result[prop] = obj[prop];
    }
  }
  return result;
}

function stringifyFilter(key: string, val: any) {
  const excludeProps = ['children'];
  return excludeProps.includes(key) ? undefined : val;
}

export function resolveNested(obj: any, propArr: string[]) {
  return propArr.reduce((prev: any, curr: string) => prev && prev[curr], obj);
}

export function isValueUnset(value: any) {
  const undefVals = [null, undefined, UNSET_DROPDOWN];
  return undefVals.includes(value);
}

export function dumpObject(obj: any) {
  console.dir(obj, {
    showHidden: false,
    depth: 2,
    colors: true,
    getters: true,
  });
}
