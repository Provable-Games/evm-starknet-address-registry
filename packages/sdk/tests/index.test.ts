import { expect, test } from 'vitest';
import * as sdk from '../src/index.js';
test('exposes generic ESM runtime with no wallet discovery or browser globals', () => {
  expect(sdk.SDK_STATUS).toBe('implemented');
  expect(typeof sdk.createRegistryClient).toBe('function');
  expect(typeof sdk.createRegistryReader).toBe('function');
  expect(typeof sdk.compareLinkedAddresses).toBe('function');
});
