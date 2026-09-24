import {
  accountAddress,
  ethereumAddress,
  feltHash,
  fromLimbs,
  nonzero,
  rpcInteger,
  unsigned,
  word,
} from './addresses.js';
import { exactKeys, failure, providerFailure, requireInput } from './errors.js';
import type {
  AccountAddress,
  BlockSnapshot,
  EthereumAddress,
  CompareLinkedAddresses,
  Hash32,
  RegistryReader,
  SigningDomain,
  TrustedDeployment,
} from './protocol.js';
import { deployment, signingDomain } from './typed-data.js';

/** Consumer-owned transport. Every class/call read MUST use the supplied concrete block. */
export interface RegistryTransport {
  getBlock(
    blockHash?: Hash32,
  ): Promise<{ readonly blockHash: Hash32; readonly timestamp: bigint }>;
  getChainId(): Promise<bigint>;
  getClassHash(
    registryAddress: AccountAddress,
    blockHash: Hash32,
  ): Promise<Hash32>;
  call(
    call: {
      readonly contractAddress: AccountAddress;
      readonly entrypoint: string;
      readonly calldata: readonly string[];
    },
    blockHash: Hash32,
  ): Promise<readonly string[]>;
}
function byteArray(text: string): string[] {
  const words: string[] = [];
  for (let offset = 0; offset + 31 <= text.length; offset += 31)
    words.push(ascii(text.slice(offset, offset + 31)).toString());
  const pending = text.slice(words.length * 31);
  return [
    words.length.toString(),
    ...words,
    ascii(pending).toString(),
    pending.length.toString(),
  ];
}
function ascii(text: string): bigint {
  let value = 0n;
  for (const character of text)
    value = (value << 8n) + BigInt(character.charCodeAt(0));
  return value;
}
function domainCalldata(d: SigningDomain): string[] {
  const u256 = (value: bigint): string[] => [
    (value & ((1n << 128n) - 1n)).toString(),
    (value >> 128n).toString(),
  ];
  return [
    ...byteArray(d.name),
    ...byteArray(d.version),
    ...u256(d.ethereumChainId),
    d.accountChainId.toString(),
    BigInt(d.registryAddress).toString(),
    ...u256(BigInt(d.salt)),
    ...u256(BigInt(d.domainSeparator)),
    ...byteArray(d.accountLabel),
    ...byteArray(d.linkStatement),
    ...byteArray(d.moveStatement),
    ...byteArray(d.revokeStatement),
    ...byteArray(d.accountNetworkName),
  ];
}
export function createRegistryReader(
  input: TrustedDeployment,
  transport: RegistryTransport,
): RegistryReader {
  const trusted = Object.freeze(deployment(input));
  const domain = signingDomain(trusted);
  async function raw(
    entrypoint: string,
    calldata: readonly string[],
    block: Hash32,
  ): Promise<readonly string[]> {
    try {
      const result = await transport.call(
        { contractAddress: trusted.registryAddress, entrypoint, calldata },
        feltHash(block),
      );
      requireInput(Array.isArray(result), 'Malformed RPC result');
      return result.map((value) => rpcInteger(value).toString());
    } catch (cause) {
      throw providerFailure(cause, 'query');
    }
  }
  async function authenticateOnce(block: Hash32): Promise<void> {
    try {
      const [chain, klass, discovered, version] = await Promise.all([
        transport.getChainId(),
        transport.getClassHash(trusted.registryAddress, feltHash(block)),
        raw('get_signing_domain', [], block),
        raw('get_version', [], block),
      ]);
      if (
        chain !== trusted.accountChainId ||
        feltHash(klass) !== trusted.classHash ||
        JSON.stringify(discovered) !== JSON.stringify(domainCalldata(domain)) ||
        version.length !== 1 ||
        version[0] !== '49'
      )
        throw failure(
          'deployment-mismatch',
          'query',
          'Registry identity or discovery does not match trusted deployment',
        );
    } catch (cause) {
      throw providerFailure(cause, 'query');
    }
  }
  const authenticating = new Map<Hash32, Promise<void>>();
  function authenticate(blockInput: Hash32): Promise<void> {
    const block = feltHash(blockInput);
    const pending = authenticating.get(block);
    if (pending) return pending;
    const result = authenticateOnce(block).finally(() => {
      authenticating.delete(block);
    });
    authenticating.set(block, result);
    return result;
  }
  async function read(
    entrypoint: string,
    calldata: readonly string[],
    block: Hash32,
  ): Promise<readonly string[]> {
    await authenticate(block);
    return raw(entrypoint, calldata, block);
  }
  function single(values: readonly string[]): bigint {
    requireInput(values.length === 1, 'Unexpected RPC result arity');
    return rpcInteger(values[0]);
  }
  function nonce(values: readonly string[]): bigint {
    requireInput(values.length === 2, 'Unexpected nonce result arity');
    return fromLimbs(values[0], values[1]);
  }
  async function countAt(
    account: AccountAddress,
    block: Hash32,
  ): Promise<bigint> {
    return unsigned(
      single(
        await raw(
          'get_ethereum_address_count',
          [BigInt(accountAddress(account)).toString()],
          block,
        ),
      ),
      64,
    );
  }
  async function pageAt(
    account: AccountAddress,
    offset: bigint,
    limit: bigint,
    block: Hash32,
  ): Promise<readonly EthereumAddress[]> {
    unsigned(offset, 64);
    unsigned(limit, 32);
    requireInput(limit >= 1n && limit <= 100n, 'Page limit must be 1..100');
    const values = await raw(
      'get_ethereum_addresses',
      [
        BigInt(accountAddress(account)).toString(),
        offset.toString(),
        limit.toString(),
      ],
      block,
    );
    requireInput(
      values.length >= 1 &&
        rpcInteger(values[0]) === BigInt(values.length - 1) &&
        BigInt(values.length - 1) <= limit,
      'Malformed page length',
    );
    return values
      .slice(1)
      .map((value) =>
        nonzero(
          ethereumAddress(
            `0x${unsigned(rpcInteger(value), 160).toString(16).padStart(40, '0')}`,
          ),
        ),
      );
  }
  const reader: RegistryReader = {
    deployment: trusted,
    async getSigningDomain(block) {
      await authenticate(block);
      return { ...domain };
    },
    async getVersion(block) {
      await authenticate(block);
      return 49n;
    },
    async getStarknetAddress(ethereum, block) {
      return accountAddress(
        word(
          single(
            await read(
              'get_starknet_address',
              [BigInt(ethereumAddress(ethereum)).toString()],
              block,
            ),
          ),
        ),
      );
    },
    async getEthereumNonce(ethereum, block) {
      return nonce(
        await read(
          'get_ethereum_nonce',
          [BigInt(ethereumAddress(ethereum)).toString()],
          block,
        ),
      );
    },
    async getRecipientNonce(account, ethereum, block) {
      return nonce(
        await read(
          'get_recipient_nonce',
          [
            BigInt(accountAddress(account)).toString(),
            BigInt(ethereumAddress(ethereum)).toString(),
          ],
          block,
        ),
      );
    },
    async isAssociated(ethereum, account, block) {
      const value = single(
        await read(
          'is_associated',
          [
            BigInt(ethereumAddress(ethereum)).toString(),
            BigInt(accountAddress(account)).toString(),
          ],
          block,
        ),
      );
      requireInput(value === 0n || value === 1n, 'Malformed native bool');
      return value === 1n;
    },
    async getEthereumAddressCount(account, block) {
      await authenticate(block);
      return countAt(account, block);
    },
    async getEthereumAddresses(account, offset, limit, block) {
      await authenticate(block);
      return pageAt(account, offset, limit, block);
    },
    async listAllEthereumAddresses(accountInput, blockInput, options) {
      const account = accountAddress(accountInput),
        block = feltHash(blockInput);
      if (options !== undefined) exactKeys(options, ['maxAddresses']);
      const maximum = unsigned(
        options === undefined ? 10_000n : options.maxAddresses,
        64,
      );
      await authenticate(block);
      const count = await countAt(account, block);
      requireInput(
        count <= maximum,
        'Reverse collection exceeds enumeration budget',
      );
      const addresses: EthereumAddress[] = [];
      const seen = new Set<EthereumAddress>();
      for (let offset = 0n; offset < count; offset += 100n) {
        const page = await pageAt(account, offset, 100n, block);
        requireInput(
          BigInt(page.length) ===
            (count - offset < 100n ? count - offset : 100n),
          'Incomplete pinned page',
        );
        for (const address of page) {
          requireInput(!seen.has(address), 'Duplicate pinned reverse entry');
          seen.add(address);
          addresses.push(address);
        }
      }
      return {
        deployment: trusted,
        accountAddress: account,
        blockHash: block,
        ethereumAddresses: addresses,
      };
    },
    async snapshot(requested, ethereumInput, accountInput, blockInput) {
      const requestedDeployment = deployment(requested);
      requireInput(
        Object.entries(trusted).every(
          ([key, value]) =>
            requestedDeployment[key as keyof TrustedDeployment] === value,
        ),
        'Reader deployment mismatch',
      );
      const ethereum = ethereumAddress(ethereumInput),
        account = nonzero(accountAddress(accountInput));
      try {
        const header = await transport.getBlock(blockInput);
        const block = feltHash(header.blockHash);
        requireInput(
          blockInput === undefined || block === feltHash(blockInput),
          'Block header mismatch',
        );
        const [current, ethNonce, recipient] = await Promise.all([
          reader.getStarknetAddress(ethereum, block),
          reader.getEthereumNonce(ethereum, block),
          reader.getRecipientNonce(account, ethereum, block),
        ]);
        const result: BlockSnapshot = {
          blockHash: block,
          timestamp: unsigned(header.timestamp, 64),
          classHash: trusted.classHash,
          signingDomain: { ...domain },
          ethereumAddress: ethereum,
          accountAddress: account,
          currentAccountAddress: current,
          ethereumNonce: ethNonce,
          recipientNonce: recipient,
        };
        return result;
      } catch (cause) {
        throw providerFailure(cause, 'query');
      }
    },
  };
  return reader;
}
export const compareLinkedAddresses: CompareLinkedAddresses = (
  snapshot,
  allowed,
) => {
  const linked = [...new Set(snapshot.ethereumAddresses.map(ethereumAddress))],
    normalizedAllowedAddresses = [...new Set(allowed.map(ethereumAddress))],
    allowedSet = new Set(normalizedAllowedAddresses);
  return {
    snapshot: {
      deployment: deployment(snapshot.deployment),
      blockHash: feltHash(snapshot.blockHash),
      accountAddress: accountAddress(snapshot.accountAddress),
      ethereumAddresses: linked,
    },
    normalizedAllowedAddresses,
    matches: linked.filter((address) => allowedSet.has(address)),
  };
};
