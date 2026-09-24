/** Runtime availability does not imply deployment or tested wallet compatibility. */
export const SDK_STATUS = 'implemented' as const;
export type {
  AddressComparison,
  CompareLinkedAddresses,
  LinkedAddressSnapshot,
  ReadbackObservation,
  ReadbackResult,
  SubmissionResult,
  SuccessfulTransactionReceipt,
  AccountAdapter,
  AccountChangeReason,
  AccountAddress,
  BlockSnapshot,
  EthereumAddress,
  EthereumProvider,
  Hash32,
  Hex,
  LinkRequest,
  MoveRequest,
  Operation,
  PreparedRequest,
  ProtocolRevision,
  RegistryCall,
  RegistryClient,
  RegistryClientError,
  RegistryRevertCode,
  RegistryReader,
  RevokeRequest,
  Signature,
  SignedRequest,
  SigningDomain,
  TransactionReceipt,
  TrustedDeployment,
  TypedData,
  TypedField,
} from './protocol.js';

export { createRegistryClient } from './client.js';
export type { RegistryClientOptions } from './client.js';
export { createRegistryReader, compareLinkedAddresses } from './queries.js';
export type { RegistryTransport } from './queries.js';
export {
  ethereumAddress,
  accountAddress,
  feltHash,
  hash32,
  word,
} from './addresses.js';
export { parseSignature, recoverSigner, signatureHex } from './signature.js';
export {
  signingDomain,
  typedDigest,
  walletTypedData,
  PROTOCOL_REVISION,
  ABI_SHA256,
} from './typed-data.js';
