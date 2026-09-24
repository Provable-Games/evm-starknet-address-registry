/** Frozen public protocol agreement. Runtime factories implement these interfaces. */
export type Hex = `0x${string}`;
/** Canonical lowercase 0x + exactly 40 hex digits internally; ERC-55 only for display.
 * These structural aliases are mutually assignable and provide no nominal width safety.
 * Runtime code must validate all untrusted inputs before normalization.
 */
export type EthereumAddress = Hex;
/** Canonical lowercase 0x + exactly 64 hex digits; validate the native range for each context. */
export type AccountAddress = Hex;
/** Canonical lowercase 32-byte word; validate native felt bounds when used for chain hashes. */
export type Hash32 = Hex;
export type Operation = 'link' | 'move' | 'revoke';
export type ProtocolRevision = '5beae0d4f74dfc4ed9cc664db98d28e5c4f5b96a';

export interface Signature {
  readonly r: bigint;
  readonly s: bigint;
  readonly yParity: boolean;
}
export interface LinkRequest {
  readonly ethereumAddress: EthereumAddress;
  readonly accountAddress: AccountAddress;
  readonly ethereumNonce: bigint;
  readonly recipientNonce: bigint;
  readonly deadline: bigint;
}
export interface MoveRequest {
  readonly ethereumAddress: EthereumAddress;
  readonly accountAddress: AccountAddress;
  readonly previousAccountAddress: AccountAddress;
  readonly ethereumNonce: bigint;
  readonly recipientNonce: bigint;
  readonly deadline: bigint;
}
export interface RevokeRequest {
  readonly ethereumAddress: EthereumAddress;
  readonly currentAccountAddress: AccountAddress;
  readonly ethereumNonce: bigint;
  readonly deadline: bigint;
}
export interface TrustedDeployment {
  readonly ethereumChainId: 1n | 11155111n;
  readonly accountChainId: bigint;
  readonly registryAddress: AccountAddress;
  readonly classHash: Hash32;
  readonly accountLabel: string;
  readonly protocolRevision: ProtocolRevision;
  readonly abiSha256: string;
}
export interface SigningDomain {
  readonly name: 'Account Address Association';
  readonly version: '1';
  readonly ethereumChainId: bigint;
  readonly accountChainId: bigint;
  readonly registryAddress: AccountAddress;
  readonly salt: Hash32;
  readonly domainSeparator: Hash32;
  readonly accountLabel: string;
  readonly linkStatement: string;
  readonly moveStatement: string;
  readonly revokeStatement: string;
  readonly accountNetworkName: 'Starknet Mainnet' | 'Starknet Sepolia';
}
export interface BlockSnapshot {
  readonly blockHash: Hash32;
  readonly timestamp: bigint;
  readonly classHash: Hash32;
  readonly signingDomain: SigningDomain;
  readonly ethereumAddress: EthereumAddress;
  readonly accountAddress: AccountAddress;
  readonly currentAccountAddress: AccountAddress;
  readonly ethereumNonce: bigint;
  readonly recipientNonce: bigint;
}
export interface TypedField<
  Name extends string = string,
  Type extends string = string,
> {
  readonly name: Name;
  readonly type: Type;
}
interface TypedDataDomain {
  readonly name: 'Account Address Association';
  readonly version: '1';
  readonly chainId: string;
  readonly salt: Hash32;
  readonly verifyingContract?: never;
}
type EIP712DomainFields = readonly [
  TypedField<'name', 'string'>,
  TypedField<'version', 'string'>,
  TypedField<'chainId', 'uint256'>,
  TypedField<'salt', 'bytes32'>,
];
type LinkAddressFields = readonly [
  TypedField<'statement', 'string'>,
  TypedField<'ethereumAddress', 'address'>,
  TypedField<'accountAddress', 'bytes32'>,
  TypedField<'accountChainId', 'uint256'>,
  TypedField<'registryAddress', 'bytes32'>,
  TypedField<'ethereumNonce', 'uint256'>,
  TypedField<'recipientNonce', 'uint256'>,
  TypedField<'deadline', 'uint64'>,
];
type MoveAddressFields = readonly [
  TypedField<'statement', 'string'>,
  TypedField<'ethereumAddress', 'address'>,
  TypedField<'accountAddress', 'bytes32'>,
  TypedField<'previousAccountAddress', 'bytes32'>,
  TypedField<'accountChainId', 'uint256'>,
  TypedField<'registryAddress', 'bytes32'>,
  TypedField<'ethereumNonce', 'uint256'>,
  TypedField<'recipientNonce', 'uint256'>,
  TypedField<'deadline', 'uint64'>,
];
type RevokeAssociationFields = readonly [
  TypedField<'statement', 'string'>,
  TypedField<'ethereumAddress', 'address'>,
  TypedField<'currentAccountAddress', 'bytes32'>,
  TypedField<'accountChainId', 'uint256'>,
  TypedField<'registryAddress', 'bytes32'>,
  TypedField<'ethereumNonce', 'uint256'>,
  TypedField<'deadline', 'uint64'>,
];
/** JSON-safe exact operation agreement; integers are canonical decimal strings.
 * Runtime code must also reject unknown keys and validate values.
 */
export type TypedData =
  | {
      readonly primaryType: 'LinkAddress';
      readonly domain: TypedDataDomain;
      readonly types: {
        readonly EIP712Domain: EIP712DomainFields;
        readonly LinkAddress: LinkAddressFields;
        readonly MoveAddress?: never;
        readonly RevokeAssociation?: never;
      };
      readonly message: {
        readonly statement: string;
        readonly ethereumAddress: EthereumAddress;
        readonly accountAddress: AccountAddress;
        readonly accountChainId: string;
        readonly registryAddress: AccountAddress;
        readonly ethereumNonce: string;
        readonly recipientNonce: string;
        readonly deadline: string;
        readonly previousAccountAddress?: never;
        readonly currentAccountAddress?: never;
      };
    }
  | {
      readonly primaryType: 'MoveAddress';
      readonly domain: TypedDataDomain;
      readonly types: {
        readonly EIP712Domain: EIP712DomainFields;
        readonly MoveAddress: MoveAddressFields;
        readonly LinkAddress?: never;
        readonly RevokeAssociation?: never;
      };
      readonly message: {
        readonly statement: string;
        readonly ethereumAddress: EthereumAddress;
        readonly accountAddress: AccountAddress;
        readonly previousAccountAddress: AccountAddress;
        readonly accountChainId: string;
        readonly registryAddress: AccountAddress;
        readonly ethereumNonce: string;
        readonly recipientNonce: string;
        readonly deadline: string;
        readonly currentAccountAddress?: never;
      };
    }
  | {
      readonly primaryType: 'RevokeAssociation';
      readonly domain: TypedDataDomain;
      readonly types: {
        readonly EIP712Domain: EIP712DomainFields;
        readonly RevokeAssociation: RevokeAssociationFields;
        readonly LinkAddress?: never;
        readonly MoveAddress?: never;
      };
      readonly message: {
        readonly statement: string;
        readonly ethereumAddress: EthereumAddress;
        readonly currentAccountAddress: AccountAddress;
        readonly accountChainId: string;
        readonly registryAddress: AccountAddress;
        readonly ethereumNonce: string;
        readonly deadline: string;
        readonly accountAddress?: never;
        readonly previousAccountAddress?: never;
        readonly recipientNonce?: never;
      };
    };
export type PreparedRequest = {
  readonly deployment: TrustedDeployment;
  readonly snapshot: BlockSnapshot;
  readonly digest: Hash32;
} & (
  | {
      readonly operation: 'link';
      readonly request: LinkRequest;
      readonly typedData: Extract<
        TypedData,
        { readonly primaryType: 'LinkAddress' }
      >;
    }
  | {
      readonly operation: 'move';
      readonly request: MoveRequest;
      readonly typedData: Extract<
        TypedData,
        { readonly primaryType: 'MoveAddress' }
      >;
    }
  | {
      readonly operation: 'revoke';
      readonly request: RevokeRequest;
      readonly typedData: Extract<
        TypedData,
        { readonly primaryType: 'RevokeAssociation' }
      >;
    }
);
export interface SignedRequest {
  readonly prepared: PreparedRequest;
  readonly signature: Signature;
  readonly recoveredAddress: EthereumAddress;
}
export interface RegistryCall {
  readonly contractAddress: AccountAddress;
  readonly entrypoint:
    'link' | 'move' | 'unlink' | 'revoke' | 'invalidate_pending_incoming';
  readonly calldata: readonly string[];
}
export interface TransactionReceipt {
  readonly transactionHash: Hash32;
  readonly status: 'succeeded' | 'reverted';
  readonly blockHash: Hash32;
}
/** A confirmed success remains confirmed when a later read fails or observes newer state. */
export interface SuccessfulTransactionReceipt extends TransactionReceipt {
  readonly status: 'succeeded';
}
export interface ReadbackObservation {
  readonly requestIndex: number;
  readonly ethereumAddress: EthereumAddress;
  /** Observed current forward mapping, zero when unlinked; not the requested destination. */
  readonly accountAddress: AccountAddress;
  readonly ethereumNonce: bigint;
  readonly recipientNonces: readonly {
    readonly accountAddress: AccountAddress;
    readonly nonce: bigint;
  }[];
}
export type ReadbackResult =
  | {
      readonly status: 'matched' | 'mismatch';
      readonly blockHash: Hash32;
      readonly observations: readonly ReadbackObservation[];
    }
  | {
      readonly status: 'unavailable';
      readonly blockHash: Hash32;
      readonly cause: unknown;
    };
export interface SubmissionResult {
  readonly receipt: SuccessfulTransactionReceipt;
  /** readback.blockHash must equal receipt.blockHash, including unavailable reads. */
  readonly readback: ReadbackResult;
}
export interface LinkedAddressSnapshot {
  readonly deployment: TrustedDeployment;
  readonly accountAddress: AccountAddress;
  readonly blockHash: Hash32;
  readonly ethereumAddresses: readonly EthereumAddress[];
}
export interface AddressComparison {
  readonly snapshot: LinkedAddressSnapshot;
  readonly normalizedAllowedAddresses: readonly EthereumAddress[];
  readonly matches: readonly EthereumAddress[];
}
/** Pure normalized intersection only: no RPC, stored allowlist or eligibility decision. */
export type CompareLinkedAddresses = (
  snapshot: LinkedAddressSnapshot,
  allowedAddresses: readonly EthereumAddress[],
) => AddressComparison;
/** Adapters preserve provider errors and never silently choose a signing fallback. */
export interface EthereumProvider {
  request(args: {
    readonly method: string;
    readonly params?: readonly unknown[];
  }): Promise<unknown>;
  on(
    event: 'accountsChanged' | 'chainChanged' | 'disconnect',
    listener: (value: unknown) => void,
  ): void;
  removeListener(
    event: 'accountsChanged' | 'chainChanged' | 'disconnect',
    listener: (value: unknown) => void,
  ): void;
}
/** Reads must authenticate all fields at one concrete block, including the class hash. */
export interface RegistryReader {
  readonly deployment: TrustedDeployment;
  listAllEthereumAddresses(
    accountAddress: AccountAddress,
    blockHash: Hash32,
    /** Local resource budget, default 10_000n; 0n permits only an empty collection. */
    options?: { readonly maxAddresses: bigint },
  ): Promise<LinkedAddressSnapshot>;
  getEthereumNonce(
    ethereumAddress: EthereumAddress,
    blockHash: Hash32,
  ): Promise<bigint>;
  getRecipientNonce(
    accountAddress: AccountAddress,
    ethereumAddress: EthereumAddress,
    blockHash: Hash32,
  ): Promise<bigint>;
  getSigningDomain(blockHash: Hash32): Promise<SigningDomain>;
  getVersion(blockHash: Hash32): Promise<bigint>;
  snapshot(
    deployment: TrustedDeployment,
    ethereumAddress: EthereumAddress,
    accountAddress: AccountAddress,
    blockHash?: Hash32,
  ): Promise<BlockSnapshot>;
  getStarknetAddress(
    ethereumAddress: EthereumAddress,
    blockHash: Hash32,
  ): Promise<AccountAddress>;
  isAssociated(
    ethereumAddress: EthereumAddress,
    accountAddress: AccountAddress,
    blockHash: Hash32,
  ): Promise<boolean>;
  getEthereumAddressCount(
    accountAddress: AccountAddress,
    blockHash: Hash32,
  ): Promise<bigint>;
  getEthereumAddresses(
    accountAddress: AccountAddress,
    offset: bigint,
    limit: bigint,
    blockHash: Hash32,
  ): Promise<readonly EthereumAddress[]>;
}
export type AccountChangeReason =
  'account-changed' | 'chain-changed' | 'disconnected';
export interface AccountAdapter {
  /** Synchronous, nonnegative generation; increases on every identity/network/disconnect transition. */
  generation(): bigint;
  /** Synchronous registration/removal; emit every transition, including A -> B -> A. */
  subscribeChange(listener: (reason: AccountChangeReason) => void): () => void;
  identity(): Promise<{
    readonly address: AccountAddress;
    readonly chainId: bigint;
  }>;
  simulate(calls: readonly RegistryCall[]): Promise<void>;
  execute(calls: readonly RegistryCall[]): Promise<Hash32>;
  wait(transactionHash: Hash32): Promise<TransactionReceipt>;
}
/** Generic client interface implemented by createRegistryClient. */
export interface RegistryClient {
  prepareLink(
    ethereumAddress: EthereumAddress,
    deadline?: bigint,
  ): Promise<PreparedRequest>;
  prepareMove(
    ethereumAddress: EthereumAddress,
    deadline?: bigint,
  ): Promise<PreparedRequest>;
  prepareRevoke(
    ethereumAddress: EthereumAddress,
    deadline?: bigint,
  ): Promise<PreparedRequest>;
  sign(
    prepared: PreparedRequest,
    provider: EthereumProvider,
  ): Promise<SignedRequest>;
  validate(signed: SignedRequest): Promise<void>;
  encode(signed: SignedRequest): RegistryCall;
  buildUnlinkCall(ethereumAddress: EthereumAddress): RegistryCall;
  buildInvalidatePendingIncomingCall(
    ethereumAddress: EthereumAddress,
  ): RegistryCall;
  submit(signed: readonly SignedRequest[]): Promise<SubmissionResult>;
  unlink(ethereumAddress: EthereumAddress): Promise<SubmissionResult>;
  invalidatePendingIncoming(
    ethereumAddress: EthereumAddress,
  ): Promise<SubmissionResult>;
}

/** Contract codes apply only after successful native ABI decoding. */
export type RegistryRevertCode =
  | 'AR_BAD_LABEL'
  | 'AR_BAD_CHAIN_PAIR'
  | 'AR_ZERO_ADDRESS'
  | 'AR_BAD_CALLER'
  | 'AR_ALREADY_LINKED'
  | 'AR_NOT_LINKED'
  | 'AR_BAD_PREVIOUS_ACCOUNT'
  | 'AR_BAD_CURRENT_ACCOUNT'
  | 'AR_SAME_ACCOUNT'
  | 'AR_STALE_ETH_NONCE'
  | 'AR_STALE_RECIP_NONCE'
  | 'AR_BAD_DEADLINE'
  | 'AR_EXPIRED'
  | 'AR_BAD_SIGNATURE'
  | 'AR_NONCE_OVERFLOW'
  | 'AR_COUNT_OVERFLOW'
  | 'AR_BAD_PAGE_LIMIT';
/** A known submitted hash must survive any inconclusive wait; never automatically resubmit. */
export type RegistryClientError = Error &
  (
    | {
        readonly kind: 'confirmation-unavailable';
        readonly stage: 'wait';
        readonly transactionHash: Hash32;
        readonly message: string;
        readonly cause: unknown;
      }
    | {
        readonly kind:
          | 'invalid-input'
          | 'deployment-mismatch'
          | 'account-changed'
          | 'chain-changed'
          | 'disconnected'
          | 'stale-request'
          | 'expired'
          | 'invalid-signature'
          | 'user-rejected'
          | 'unsupported-method'
          | 'registry-revert'
          | 'simulation-failed'
          | 'execution-reverted'
          | 'provider';
        readonly stage:
          | 'prepare'
          | 'sign'
          | 'validate'
          | 'simulate'
          | 'execute'
          | 'wait'
          | 'readback'
          | 'query';
        readonly message: string;
        readonly registryCode?: RegistryRevertCode;
        readonly cause?: unknown;
      }
  );
