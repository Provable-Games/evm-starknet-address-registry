//! Public core secp256k1 recovery with stable application validation errors.
use starknet::EthAddress;
use starknet::eth_signature::is_eth_signature_valid;
use starknet::secp256_trait::Signature as CoreSignature;
use crate::interface::Signature;

/// The last 20 bytes of `keccak256` of 64 zero bytes: the address core `is_eth_signature_valid`
/// derives for a signature that recovers to the point at infinity. With any `k`, `R = kG`,
/// `r = R.x` and `s = digest / k`, such a signature exists for every digest and needs no key, so
/// no signature can authorize this address.
pub const INFINITY_ETH_ADDRESS: felt252 = 0x3f17f1962b36e491b30a40b2405849e597ba5fb5;

pub fn verify(digest: u256, signature: Signature, address: EthAddress) {
    let signer: felt252 = address.into();
    assert(signer != INFINITY_ETH_ADDRESS, 'AR_BAD_SIGNATURE');
    let Signature { r, s, y_parity } = signature;
    assert(
        is_eth_signature_valid(digest, CoreSignature { r, s, y_parity }, address).is_ok(),
        'AR_BAD_SIGNATURE',
    );
}
