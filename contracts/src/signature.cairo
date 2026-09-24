//! Public core secp256k1 recovery with stable application validation errors.
use starknet::EthAddress;
use starknet::eth_signature::is_eth_signature_valid;
use starknet::secp256_trait::Signature as CoreSignature;
use crate::interface::Signature;
pub fn verify(digest: u256, signature: Signature, address: EthAddress) {
    let Signature { r, s, y_parity } = signature;
    assert(
        is_eth_signature_valid(digest, CoreSignature { r, s, y_parity }, address).is_ok(),
        'AR_BAD_SIGNATURE',
    );
}
