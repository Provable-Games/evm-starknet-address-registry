import {
  compareLinkedAddresses,
  type AccountAddress,
  type AddressComparison,
  type EthereumAddress,
  type Hash32,
  type RegistryReader,
} from '@provable-games/evm-starknet-address-registry';

/** Render this discriminated state; a read failure never becomes an empty list. */
export type PreviewState =
  | { readonly status: 'loading' }
  | { readonly status: 'error'; readonly error: unknown }
  | {
      readonly status: 'ready';
      readonly comparison: AddressComparison;
      readonly promptRegistration: boolean;
      readonly canAddWallet: true;
    };

/** Obtain blockHash from the application's concrete-block transport first. */
export async function loadAssociationPreview(
  reader: RegistryReader,
  account: AccountAddress,
  blockHash: Hash32,
  allowed: readonly EthereumAddress[],
  render: (state: PreviewState) => void,
): Promise<void> {
  render({ status: 'loading' });
  try {
    const snapshot = await reader.listAllEthereumAddresses(account, blockHash);
    render({
      status: 'ready',
      comparison: compareLinkedAddresses(snapshot, allowed),
      promptRegistration: snapshot.ethereumAddresses.length === 0,
      canAddWallet: true,
    });
  } catch (error) {
    render({ status: 'error', error });
  }
}
