// Compile/lint-only agreement fixture; no production error implementation is supplied.
import type { RegistryClientError } from '../src/index.js';

export function throwDeclaredError(error: RegistryClientError): never {
  throw error;
}

export function rejectDeclaredError(
  error: RegistryClientError,
): Promise<never> {
  return Promise.reject(error);
}
