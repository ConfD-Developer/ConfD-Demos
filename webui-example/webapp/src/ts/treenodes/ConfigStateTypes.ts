import type { QTree } from 'quasar';
import type TaskHandler from '../tasks/TaskHandler';

export interface ListMeta {
  total: number;
  position: number;
  chunk_size: number;
  lh: number;
}

export type ScalarValue = string | number | boolean | null;
export type LeafListValue = ScalarValue[];

// TODO - investigate list meta binding instead of actual values)
export type ConfigNodeValue = ScalarValue | LeafListValue;
export type ConfigStateEntry = ConfigNodeValue | ListMeta;

export type ConfigState = Record<string, ConfigStateEntry | undefined>;

export interface ConfigContext {
  state: ConfigState;
  tasker: TaskHandler;
  tree: QTree;
}
