// Dev-only bridge: starknet 10.8.0's WalletAccountV6 declaration has upstream
// TS2417. Strict SDK/consumer TypeScript checks remain enabled. The typed port
// treats every RPC result as unknown; transport.ts validates it before SDK use.
import { Account, RpcProvider, selector } from 'starknet';

export function nativeSelector(name) {
  return selector.getSelectorFromName(name);
}

export function createNativeAccount(url, address, publicTestPrivateKey) {
  const account = new Account({
    provider: new RpcProvider({ nodeUrl: url }),
    address,
    signer: publicTestPrivateKey,
    cairoVersion: '1',
  });
  return Object.freeze({
    address,
    simulate: (calls) =>
      account.simulateTransaction([{ type: 'INVOKE', payload: calls }], {
        skipValidate: false,
        tip: 0,
      }),
    execute: (calls) => account.execute(calls, { tip: 0 }),
    wait: (transactionHash) =>
      account.provider.waitForTransaction(transactionHash),
  });
}
