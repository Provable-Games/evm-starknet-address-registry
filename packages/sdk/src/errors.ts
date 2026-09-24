import type { Hash32, RegistryClientError } from './protocol.js';

const ownedErrors = new WeakSet<Error>();

type OrdinaryError = Exclude<
  RegistryClientError,
  { kind: 'confirmation-unavailable' }
>;
export type ErrorKind = OrdinaryError['kind'];
export type ErrorStage = OrdinaryError['stage'];

export function failure(
  kind: ErrorKind,
  stage: ErrorStage,
  message: string,
  cause?: unknown,
): RegistryClientError {
  const error = Object.assign(new Error(message, { cause }), {
    name: 'RegistryClientError',
    kind,
    stage,
  });
  ownedErrors.add(error);
  return error;
}
export function confirmationUnavailable(
  transactionHash: Hash32,
  cause: unknown,
): RegistryClientError {
  const error = Object.assign(
    new Error(
      'Transaction submitted; confirmation unavailable. Reconcile its hash before retrying.',
      { cause },
    ),
    {
      name: 'RegistryClientError',
      kind: 'confirmation-unavailable' as const,
      stage: 'wait' as const,
      transactionHash,
      cause,
    },
  );
  ownedErrors.add(error);
  return error;
}
export function requireInput(
  condition: unknown,
  message: string,
): asserts condition {
  if (!condition) throw failure('invalid-input', 'validate', message);
}
export function providerFailure(
  cause: unknown,
  stage: ErrorStage,
): RegistryClientError {
  if (cause instanceof Error && ownedErrors.has(cause))
    return cause as RegistryClientError;
  const code =
    typeof cause === 'object' && cause !== null && 'code' in cause
      ? cause.code
      : undefined;
  const kind =
    code === 4001
      ? 'user-rejected'
      : code === 4200 || code === -32601
        ? 'unsupported-method'
        : code === 4900 || code === 4901
          ? 'disconnected'
          : 'provider';
  return failure(kind, stage, 'Provider request failed', cause);
}
export function exactKeys(value: unknown, keys: readonly string[]): void {
  requireInput(
    typeof value === 'object' &&
      value !== null &&
      Object.keys(value).length === keys.length &&
      keys.every((key) => Object.hasOwn(value, key)),
    'Unexpected or missing fields',
  );
}

export function isValue(actual: unknown, expected: unknown): boolean {
  return actual === expected;
}
