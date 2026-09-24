import { recoverAddress } from 'viem/utils';
import { ethereumAddress, limbs, nonzero, word } from './addresses.js';
import { exactKeys, failure, requireInput } from './errors.js';
import type {
  EthereumAddress,
  Hash32,
  Hex,
  RegistryCall,
  Signature,
  SignedRequest,
} from './protocol.js';
import { authenticatePrepared } from './typed-data.js';

export const SECP256K1_ORDER =
  0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141n;
export function checkedSignature(value: Signature): Signature {
  exactKeys(value, ['r', 's', 'yParity']);
  requireInput(
    typeof value.r === 'bigint' &&
      value.r > 0n &&
      value.r < SECP256K1_ORDER &&
      typeof value.s === 'bigint' &&
      value.s > 0n &&
      value.s <= SECP256K1_ORDER / 2n &&
      typeof value.yParity === 'boolean',
    'Invalid signature scalar or parity',
  );
  return { r: value.r, s: value.s, yParity: value.yParity };
}
export function parseSignature(value: unknown): Signature {
  requireInput(
    typeof value === 'string' &&
      /^0x[0-9a-fA-F]+$/.test(value) &&
      (value.length === 130 || value.length === 132),
    'Expected conventional or compact signature',
  );
  const r = BigInt(`0x${value.slice(2, 66)}`),
    encodedS = BigInt(`0x${value.slice(66, 130)}`);
  if (value.length === 130)
    return checkedSignature({
      r,
      s: encodedS & ((1n << 255n) - 1n),
      yParity: encodedS >> 255n === 1n,
    });
  const v = Number.parseInt(value.slice(130), 16);
  requireInput(
    v === 0 || v === 1 || v === 27 || v === 28,
    'Unsupported signature v',
  );
  return checkedSignature({ r, s: encodedS, yParity: v === 1 || v === 28 });
}
export function signatureHex(input: Signature): Hex {
  const signature = checkedSignature(input);
  return `0x${word(signature.r).slice(2)}${word(signature.s).slice(2)}${signature.yParity ? '1c' : '1b'}`;
}
export async function recoverSigner(
  digest: Hash32,
  signature: Signature,
  expected: EthereumAddress,
): Promise<EthereumAddress> {
  const claimed = nonzero(ethereumAddress(expected));
  try {
    const recovered = ethereumAddress(
      await recoverAddress({
        hash: digest,
        signature: signatureHex(signature),
      }),
    );
    if (recovered !== claimed)
      throw failure(
        'invalid-signature',
        'validate',
        'Signature does not recover the claimed address',
      );
    return recovered;
  } catch (cause) {
    throw failure(
      'invalid-signature',
      'validate',
      'Invalid signature or recovered address',
      cause,
    );
  }
}
export function encodeSigned(input: SignedRequest): RegistryCall {
  const p = authenticatePrepared(input.prepared),
    s = checkedSignature(input.signature),
    r = p.request;
  requireInput(
    ethereumAddress(input.recoveredAddress) === r.ethereumAddress,
    'Recovered address differs from request',
  );
  const request =
    p.operation === 'revoke'
      ? [
          BigInt(r.ethereumAddress).toString(),
          BigInt(p.request.currentAccountAddress).toString(),
          ...limbs(r.ethereumNonce),
          r.deadline.toString(),
        ]
      : [
          BigInt(r.ethereumAddress).toString(),
          BigInt(p.request.accountAddress).toString(),
          ...(p.operation === 'move'
            ? [BigInt(p.request.previousAccountAddress).toString()]
            : []),
          ...limbs(r.ethereumNonce),
          ...limbs(p.request.recipientNonce),
          r.deadline.toString(),
        ];
  return {
    contractAddress: p.deployment.registryAddress,
    entrypoint: p.operation,
    calldata: [...request, ...limbs(s.r), ...limbs(s.s), s.yParity ? '1' : '0'],
  };
}
