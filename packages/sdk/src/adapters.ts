import { getAddress } from 'viem/utils';
import { ethereumAddress, rpcInteger } from './addresses.js';
import { failure, providerFailure, requireInput } from './errors.js';
import type {
  EthereumAddress,
  EthereumProvider,
  PreparedRequest,
  SignedRequest,
} from './protocol.js';
import { parseSignature, recoverSigner } from './signature.js';
import { walletTypedData } from './typed-data.js';

/** Only the injected selected provider is used; listeners exist for this attempt alone. */
export async function signWithProvider(
  prepared: PreparedRequest,
  provider: EthereumProvider,
  checks?: {
    assertActive?(): void;
    readonly cancelled?: Promise<never>;
    before(assertActive: () => void): Promise<void>;
    after(assertActive: () => void): Promise<void>;
  },
): Promise<SignedRequest> {
  const selected = prepared.request.ethereumAddress;
  let cancel!: (reason: Error) => void;
  const changed = new Promise<never>((_, reject) => {
    cancel = reject;
  });
  // A losing async task continues after Promise.race settles. Keep its invalidation
  // permanent so a late selection response can never open a new signing prompt.
  let invalidated: Error | undefined;
  function invalidate(error: Error): void {
    invalidated ??= error;
    cancel(invalidated);
  }
  function active(): void {
    checks?.assertActive?.();
    if (invalidated) throw invalidated;
  }
  // Registration itself may synchronously emit an event and throw before racing.
  void changed.catch(() => undefined);
  const accountChanged = (value: unknown): void => {
    try {
      requireInput(
        Array.isArray(value) && ethereumAddress(value[0]) === selected,
        'Selected account changed',
      );
    } catch (cause) {
      invalidate(
        failure(
          'account-changed',
          'sign',
          'Selected Ethereum account changed',
          cause,
        ),
      );
    }
  };
  const chainChanged = (value: unknown): void => {
    try {
      requireInput(
        rpcInteger(value) === prepared.deployment.ethereumChainId,
        'Selected chain changed',
      );
    } catch (cause) {
      invalidate(
        failure(
          'chain-changed',
          'sign',
          'Selected Ethereum chain changed',
          cause,
        ),
      );
    }
  };
  const disconnected = (cause: unknown): void => {
    invalidate(
      failure(
        'disconnected',
        'sign',
        'Selected Ethereum provider disconnected',
        cause,
      ),
    );
  };
  const listeners = [
    ['accountsChanged', accountChanged],
    ['chainChanged', chainChanged],
    ['disconnect', disconnected],
  ] as const;
  const installed: (typeof listeners)[number][] = [];
  async function selection(): Promise<void> {
    const accounts: unknown = await provider.request({
      method: 'eth_accounts',
    });
    active();
    requireInput(
      Array.isArray(accounts),
      'Malformed selected Ethereum accounts',
    );
    if (accounts.length === 0)
      throw failure('disconnected', 'sign', 'No selected Ethereum account');
    if (ethereumAddress(accounts[0]) !== selected)
      throw failure(
        'account-changed',
        'sign',
        'Selected Ethereum account differs from request',
      );
    const chain: unknown = await provider.request({ method: 'eth_chainId' });
    active();
    if (rpcInteger(chain) !== prepared.deployment.ethereumChainId)
      throw failure(
        'chain-changed',
        'sign',
        'Selected Ethereum chain differs from request',
      );
  }
  async function sign(): Promise<SignedRequest> {
    active();
    await checks?.before(active);
    active();
    await selection();
    active();
    const encoded: unknown = await provider.request({
      method: 'eth_signTypedData_v4',
      params: [
        getAddress(selected),
        JSON.stringify(walletTypedData(prepared.typedData)),
      ],
    });
    active();
    await selection();
    active();
    const signature = parseSignature(encoded);
    const recoveredAddress: EthereumAddress = await recoverSigner(
      prepared.digest,
      signature,
      selected,
    );
    active();
    await checks?.after(active);
    active();
    return Object.freeze({
      prepared,
      signature: Object.freeze(signature),
      recoveredAddress,
    });
  }
  let failed = false;
  try {
    for (const listener of listeners) {
      installed.push(listener);
      provider.on(listener[0], listener[1]);
    }
    return await Promise.race([
      changed,
      sign(),
      ...(checks?.cancelled ? [checks.cancelled] : []),
    ]);
  } catch (cause) {
    failed = true;
    invalidate(providerFailure(cause, 'sign'));
    throw providerFailure(cause, 'sign');
  } finally {
    const cleanupErrors: unknown[] = [];
    for (const listener of installed) {
      try {
        provider.removeListener(listener[0], listener[1]);
      } catch (cause) {
        cleanupErrors.push(cause);
      }
    }
    if (cleanupErrors.length > 0 && !failed)
      throw providerFailure(
        new AggregateError(cleanupErrors, 'Provider listener cleanup failed'),
        'sign',
      );
  }
}
