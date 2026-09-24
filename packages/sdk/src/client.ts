import {
  accountAddress,
  ethereumAddress,
  feltHash,
  nonzero,
  unsigned,
  ZERO_ACCOUNT,
} from './addresses.js';
import { signWithProvider } from './adapters.js';
import {
  confirmationUnavailable,
  failure,
  isValue,
  providerFailure,
  requireInput,
} from './errors.js';
import type {
  AccountAdapter,
  RegistryClientError,
  AccountAddress,
  BlockSnapshot,
  EthereumAddress,
  Hash32,
  Operation,
  PreparedRequest,
  ReadbackObservation,
  RegistryCall,
  RegistryClient,
  RegistryReader,
  SignedRequest,
  SubmissionResult,
  TrustedDeployment,
} from './protocol.js';
import { checkedSignature, encodeSigned, recoverSigner } from './signature.js';
import {
  authenticatePrepared,
  checkedSnapshot,
  deployment,
  prepareRequest,
} from './typed-data.js';

export interface RegistryClientOptions {
  readonly deployment: TrustedDeployment;
  readonly reader: RegistryReader;
  readonly account: AccountAdapter;
}
interface ExpectedEffect {
  readonly ethereum: EthereumAddress;
  readonly current: AccountAddress;
  readonly ethereumNonce: bigint;
  readonly pairs: readonly {
    readonly accountAddress: AccountAddress;
    readonly nonce: bigint;
  }[];
}
interface Attempt {
  readonly active: () => void;
  readonly cancelled: Promise<never>;
  finish(): void;
}
async function accountAttempt<T>(
  account: AccountAdapter,
  stage: RegistryClientError['stage'],
  action: (attempt: Attempt) => Promise<T>,
): Promise<T> {
  let invalidated: Error | undefined;
  const state = { finished: false };
  let cancel!: (error: Error) => void;
  const cancelled = new Promise<never>((_, reject) => {
    cancel = reject;
  });
  void cancelled.catch(() => undefined);
  let generation: bigint;
  let unsubscribe: (() => void) | undefined;
  let checkActive: (() => void) | undefined;
  let failed = false;
  try {
    generation = account.generation();
    requireInput(
      typeof generation === 'bigint' && generation >= 0n,
      'Malformed account generation',
    );
    function invalidate(reason: unknown): void {
      if (state.finished) return;
      const valid =
        reason === 'account-changed' ||
        reason === 'chain-changed' ||
        reason === 'disconnected';
      invalidated ??= failure(
        valid ? reason : 'invalid-input',
        stage,
        valid
          ? 'Native account changed during attempt'
          : 'Malformed account change reason',
      );
      cancel(invalidated);
    }
    function active(): void {
      if (account.generation() !== generation) invalidate('account-changed');
      if (invalidated) throw invalidated;
    }
    checkActive = active;
    const stop = account.subscribeChange(invalidate);
    unsubscribe = stop;
    function finish(): void {
      unsubscribe = undefined;
      stop();
      active();
      state.finished = true;
    }
    active();
    const result = await Promise.race([
      cancelled,
      action({ active, cancelled, finish }),
    ]);
    if (!state.finished) active();
    return result;
  } catch (cause) {
    failed = true;
    throw providerFailure(cause, stage);
  } finally {
    if (!state.finished) {
      try {
        unsubscribe?.();
        if (!failed) checkActive?.();
      } catch (cause) {
        if (!failed) throw providerFailure(cause, stage);
      } finally {
        state.finished = true;
      }
    }
  }
}
export function createRegistryClient(
  options: RegistryClientOptions,
): RegistryClient {
  const trusted = Object.freeze(deployment(options.deployment)),
    reader = options.reader,
    account = options.account;
  async function identity(attempt: Attempt): Promise<AccountAddress> {
    try {
      attempt.active();
      const current = await account.identity();
      attempt.active();
      if (current.chainId !== trusted.accountChainId)
        throw failure(
          'chain-changed',
          'validate',
          'Account chain differs from deployment',
        );
      return nonzero(accountAddress(current.address));
    } catch (cause) {
      throw providerFailure(cause, 'validate');
    }
  }
  async function snapshot(
    ethereum: EthereumAddress,
    destination: AccountAddress,
    attempt: Attempt,
    blockHash?: Hash32,
  ): Promise<BlockSnapshot> {
    try {
      attempt.active();
      const result = checkedSnapshot(
        trusted,
        await reader.snapshot(trusted, ethereum, destination, blockHash),
      );
      attempt.active();
      requireInput(
        blockHash === undefined || result.blockHash === blockHash,
        'Snapshot block mismatch',
      );
      requireInput(
        result.ethereumAddress === ethereum &&
          result.accountAddress === destination,
        'Snapshot request identity mismatch',
      );
      return result;
    } catch (cause) {
      throw providerFailure(cause, 'prepare');
    }
  }
  async function prepare(
    operation: Operation,
    ethereumInput: EthereumAddress,
    deadline: bigint | undefined,
    attempt: Attempt,
  ): Promise<PreparedRequest> {
    // Revocation signs the current association, not a recipient pair. The
    // registry address is a stable nonzero account for the query-only snapshot.
    const destination =
        operation === 'revoke'
          ? trusted.registryAddress
          : await identity(attempt),
      ethereum = nonzero(ethereumAddress(ethereumInput));
    const current = await snapshot(ethereum, destination, attempt);
    if (operation !== 'revoke' && (await identity(attempt)) !== destination)
      throw failure(
        'account-changed',
        'prepare',
        'Account changed while preparing',
      );
    return prepareRequest(trusted, current, operation, deadline);
  }
  function configured(prepared: PreparedRequest): PreparedRequest {
    const valid = authenticatePrepared(prepared),
      d = valid.deployment;
    requireInput(
      Object.entries(trusted).every(
        ([key, value]) => d[key as keyof TrustedDeployment] === value,
      ),
      'Prepared deployment differs from client configuration',
    );
    return valid;
  }
  async function currentRequest(
    prepared: PreparedRequest,
    attempt: Attempt,
    assertActive: () => void = attempt.active,
    blockHash?: Hash32,
  ): Promise<BlockSnapshot> {
    const p = configured(prepared),
      destination =
        p.operation === 'revoke'
          ? p.snapshot.accountAddress
          : await identity(attempt);
    assertActive();
    if (p.operation !== 'revoke' && destination !== p.request.accountAddress)
      throw failure(
        'account-changed',
        'validate',
        'Connected account is not the signed destination',
      );
    const state = await snapshot(
      p.request.ethereumAddress,
      destination,
      attempt,
      blockHash,
    );
    assertActive();
    if (state.timestamp > p.request.deadline)
      throw failure('expired', 'validate', 'Request deadline has passed');
    if (
      state.ethereumNonce !== p.request.ethereumNonce ||
      state.currentAccountAddress !== p.snapshot.currentAccountAddress ||
      (p.operation !== 'revoke' &&
        state.recipientNonce !== p.request.recipientNonce)
    )
      throw failure(
        'stale-request',
        'validate',
        'Association or current nonce changed; prepare a new request',
      );
    if (p.operation !== 'revoke' && (await identity(attempt)) !== destination)
      throw failure(
        'account-changed',
        'validate',
        'Account changed during validation',
      );
    assertActive();
    return state;
  }
  async function validate(
    signed: SignedRequest,
    attempt: Attempt,
    blockHash?: Hash32,
  ): Promise<BlockSnapshot> {
    const p = configured(signed.prepared);
    requireInput(
      ethereumAddress(signed.recoveredAddress) === p.request.ethereumAddress,
      'Stored recovered signer differs',
    );
    await recoverSigner(p.digest, signed.signature, p.request.ethereumAddress);
    attempt.active();
    return currentRequest(p, attempt, attempt.active, blockHash);
  }
  async function pair(
    pairAccount: AccountAddress,
    ethereum: EthereumAddress,
    block: Hash32,
  ): Promise<bigint> {
    return unsigned(
      await reader.getRecipientNonce(pairAccount, ethereum, block),
      256,
    );
  }
  async function signedEffect(
    signed: SignedRequest,
    state: BlockSnapshot,
  ): Promise<ExpectedEffect> {
    try {
      const p = signed.prepared,
        pairs: { accountAddress: AccountAddress; nonce: bigint }[] = [];
      if (state.currentAccountAddress !== ZERO_ACCOUNT)
        pairs.push({
          accountAddress: state.currentAccountAddress,
          nonce: unsigned(
            (await pair(
              state.currentAccountAddress,
              state.ethereumAddress,
              state.blockHash,
            )) + 1n,
            256,
          ),
        });
      if (p.operation !== 'revoke')
        pairs.push({
          accountAddress: p.request.accountAddress,
          nonce: unsigned(state.recipientNonce + 1n, 256),
        });
      return {
        ethereum: state.ethereumAddress,
        current:
          p.operation === 'revoke' ? ZERO_ACCOUNT : p.request.accountAddress,
        ethereumNonce: unsigned(state.ethereumNonce + 1n, 256),
        pairs,
      };
    } catch (cause) {
      throw providerFailure(cause, 'validate');
    }
  }

  async function readback(
    receipt: SubmissionResult['receipt'],
    expected: readonly ExpectedEffect[],
  ): Promise<SubmissionResult> {
    try {
      const observations: ReadbackObservation[] = [];
      let matched = true;
      for (const [index, effect] of expected.entries()) {
        const [mapping, nonce, pairs] = await Promise.all([
          reader.getStarknetAddress(effect.ethereum, receipt.blockHash),
          reader.getEthereumNonce(effect.ethereum, receipt.blockHash),
          Promise.all(
            effect.pairs.map(async (entry) => ({
              accountAddress: entry.accountAddress,
              nonce: await pair(
                entry.accountAddress,
                effect.ethereum,
                receipt.blockHash,
              ),
            })),
          ),
        ]);
        const observed = {
          requestIndex: index,
          ethereumAddress: effect.ethereum,
          accountAddress: accountAddress(mapping),
          ethereumNonce: unsigned(nonce, 256),
          recipientNonces: pairs,
        };
        observations.push(observed);
        if (
          observed.accountAddress !== effect.current ||
          observed.ethereumNonce !== effect.ethereumNonce ||
          pairs.some(
            (entry, position) => entry.nonce !== effect.pairs[position]?.nonce,
          )
        )
          matched = false;
      }
      return {
        receipt,
        readback: {
          status: matched ? 'matched' : 'mismatch',
          blockHash: receipt.blockHash,
          observations,
        },
      };
    } catch (cause) {
      return {
        receipt,
        readback: {
          status: 'unavailable',
          blockHash: receipt.blockHash,
          cause,
        },
      };
    }
  }
  async function execute(
    calls: readonly RegistryCall[],
    expected: readonly ExpectedEffect[],
    destination: AccountAddress,
    attempt: Attempt,
  ): Promise<SubmissionResult> {
    attempt.active();
    try {
      await account.simulate(calls);
    } catch (cause) {
      throw failure(
        'simulation-failed',
        'simulate',
        'Account simulation failed',
        cause,
      );
    }
    attempt.active();
    if ((await identity(attempt)) !== destination)
      throw failure(
        'account-changed',
        'execute',
        'Account changed before execution',
      );
    attempt.finish();
    let hash: Hash32;
    try {
      hash = feltHash(await account.execute(calls));
    } catch (cause) {
      throw providerFailure(cause, 'execute');
    }
    let receipt;
    try {
      receipt = await account.wait(hash);
      requireInput(
        feltHash(receipt.transactionHash) === hash &&
          (isValue(receipt.status, 'succeeded') ||
            isValue(receipt.status, 'reverted')),
        'Malformed or mismatched receipt',
      );
      receipt = {
        transactionHash: hash,
        status: receipt.status,
        blockHash: feltHash(receipt.blockHash),
      };
    } catch (cause) {
      throw confirmationUnavailable(hash, cause);
    }
    if (receipt.status === 'reverted')
      throw failure(
        'execution-reverted',
        'wait',
        'Transaction execution reverted',
        receipt,
      );
    return readback({ ...receipt, status: 'succeeded' }, expected);
  }
  function unsignedCall(
    ethereum: EthereumAddress,
    entrypoint: 'unlink' | 'invalidate_pending_incoming',
  ): RegistryCall {
    return {
      contractAddress: trusted.registryAddress,
      entrypoint,
      calldata: [BigInt(nonzero(ethereumAddress(ethereum))).toString()],
    };
  }
  async function unsignedSubmit(
    ethereumInput: EthereumAddress,
    cancel: boolean,
    attempt: Attempt,
  ): Promise<SubmissionResult> {
    const ethereum = nonzero(ethereumAddress(ethereumInput)),
      destination = await identity(attempt),
      state = await snapshot(ethereum, destination, attempt);
    if (!cancel && state.currentAccountAddress !== destination)
      throw failure(
        'stale-request',
        'validate',
        'Only the current linked account can unlink',
      );
    const expected: ExpectedEffect = {
      ethereum,
      current: cancel ? state.currentAccountAddress : ZERO_ACCOUNT,
      ethereumNonce: unsigned(state.ethereumNonce + (cancel ? 0n : 1n), 256),
      pairs: [
        {
          accountAddress: destination,
          nonce: unsigned(state.recipientNonce + 1n, 256),
        },
      ],
    };
    if ((await identity(attempt)) !== destination)
      throw failure(
        'account-changed',
        'execute',
        'Account changed before simulation',
      );
    return execute(
      [
        unsignedCall(
          ethereum,
          cancel ? 'invalidate_pending_incoming' : 'unlink',
        ),
      ],
      [expected],
      destination,
      attempt,
    );
  }
  return {
    prepareLink: (ethereum, deadline) =>
      accountAttempt(account, 'prepare', (attempt) =>
        prepare('link', ethereum, deadline, attempt),
      ),
    prepareMove: (ethereum, deadline) =>
      accountAttempt(account, 'prepare', (attempt) =>
        prepare('move', ethereum, deadline, attempt),
      ),
    prepareRevoke: (ethereum, deadline) =>
      accountAttempt(account, 'prepare', (attempt) =>
        prepare('revoke', ethereum, deadline, attempt),
      ),
    async sign(input, provider) {
      return accountAttempt(account, 'sign', async (attempt) => {
        const prepared = configured(input);
        let destination: AccountAddress;
        return signWithProvider(prepared, provider, {
          cancelled: attempt.cancelled,
          assertActive: attempt.active,
          async before(assertActive) {
            if (prepared.operation !== 'revoke') {
              destination = await identity(attempt);
              assertActive();
            }
            await currentRequest(prepared, attempt, assertActive);
          },
          async after(assertActive) {
            if (
              prepared.operation !== 'revoke' &&
              (await identity(attempt)) !== destination
            )
              throw failure(
                'account-changed',
                'sign',
                'Account changed during Ethereum signing',
              );
            assertActive();
          },
        });
      });
    },
    async validate(signed) {
      await accountAttempt(account, 'validate', (attempt) =>
        validate(signed, attempt),
      );
    },
    encode(signed) {
      configured(signed.prepared);
      return encodeSigned(signed);
    },
    buildUnlinkCall: (ethereum) => unsignedCall(ethereum, 'unlink'),
    buildInvalidatePendingIncomingCall: (ethereum) =>
      unsignedCall(ethereum, 'invalidate_pending_incoming'),
    async submit(input) {
      return accountAttempt(account, 'validate', async (attempt) => {
        const signed = input.map((value) => ({
          prepared: configured(value.prepared),
          signature: checkedSignature(value.signature),
          recoveredAddress: ethereumAddress(value.recoveredAddress),
        }));
        requireInput(
          signed.length > 0 &&
            new Set(
              signed.map((request) =>
                ethereumAddress(request.prepared.request.ethereumAddress),
              ),
            ).size === signed.length,
          'Batch requires independent Ethereum requests',
        );
        const destination = await identity(attempt),
          effects: ExpectedEffect[] = [],
          calls: RegistryCall[] = [];
        let blockHash: Hash32 | undefined;
        for (const request of signed) {
          const state = await validate(request, attempt, blockHash);
          blockHash = state.blockHash;
          effects.push(await signedEffect(request, state));
          attempt.active();
          calls.push(encodeSigned(request));
        }
        if ((await identity(attempt)) !== destination)
          throw failure(
            'account-changed',
            'execute',
            'Account changed before simulation',
          );
        return execute(calls, effects, destination, attempt);
      });
    },
    unlink: (ethereum) =>
      accountAttempt(account, 'validate', (attempt) =>
        unsignedSubmit(ethereum, false, attempt),
      ),
    invalidatePendingIncoming: (ethereum) =>
      accountAttempt(account, 'validate', (attempt) =>
        unsignedSubmit(ethereum, true, attempt),
      ),
  };
}
