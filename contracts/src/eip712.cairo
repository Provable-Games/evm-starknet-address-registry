//! Exact approved EIP-712 encodings; digest values use conventional big-endian numeric form.
use core::integer::u128_byte_reverse;
use core::keccak::{compute_keccak_byte_array, keccak_u256s_be_inputs};
use starknet::{ContractAddress, EthAddress};
use crate::interface::{LinkRequest, MoveRequest, RevokeRequest};
pub fn conventional(raw: u256) -> u256 {
    u256 { low: u128_byte_reverse(raw.high), high: u128_byte_reverse(raw.low) }
}
pub fn hash_text(text: @ByteArray) -> u256 {
    conventional(compute_keccak_byte_array(text))
}
pub fn hash_words(words: Span<u256>) -> u256 {
    conventional(keccak_u256s_be_inputs(words))
}
pub fn account_word(address: ContractAddress) -> u256 {
    let value: felt252 = address.into();
    value.into()
}
pub fn ethereum_word(address: EthAddress) -> u256 {
    let value: felt252 = address.into();
    value.into()
}
pub fn salt(chain: felt252, registry: ContractAddress) -> u256 {
    hash_words(
        array![hash_text(@"Account Address Association/v1"), chain.into(), account_word(registry)]
            .span(),
    )
}
pub fn domain(ethereum_chain: u256, salt: u256) -> u256 {
    hash_words(
        array![
            hash_text(@"EIP712Domain(string name,string version,uint256 chainId,bytes32 salt)"),
            hash_text(@"Account Address Association"), hash_text(@"1"), ethereum_chain, salt,
        ]
            .span(),
    )
}
pub fn append_word(ref bytes: ByteArray, word: u256) {
    bytes.append_word(word.high.into(), 16);
    bytes.append_word(word.low.into(), 16);
}
pub fn envelope(domain: u256, message: u256) -> u256 {
    let mut bytes: ByteArray = "";
    bytes.append_byte(0x19);
    bytes.append_byte(0x01);
    append_word(ref bytes, domain);
    append_word(ref bytes, message);
    hash_text(@bytes)
}
pub fn link_hash(
    request: @LinkRequest, statement: u256, chain: felt252, registry: ContractAddress,
) -> u256 {
    hash_words(
        array![
            hash_text(
                @"LinkAddress(string statement,address ethereumAddress,bytes32 accountAddress,uint256 accountChainId,bytes32 registryAddress,uint256 ethereumNonce,uint256 recipientNonce,uint64 deadline)",
            ),
            statement, ethereum_word(*request.ethereum_address),
            account_word(*request.account_address), chain.into(), account_word(registry),
            *request.ethereum_nonce, *request.recipient_nonce, (*request.deadline).into(),
        ]
            .span(),
    )
}
pub fn move_hash(
    request: @MoveRequest, statement: u256, chain: felt252, registry: ContractAddress,
) -> u256 {
    hash_words(
        array![
            hash_text(
                @"MoveAddress(string statement,address ethereumAddress,bytes32 accountAddress,bytes32 previousAccountAddress,uint256 accountChainId,bytes32 registryAddress,uint256 ethereumNonce,uint256 recipientNonce,uint64 deadline)",
            ),
            statement, ethereum_word(*request.ethereum_address),
            account_word(*request.account_address), account_word(*request.previous_account_address),
            chain.into(), account_word(registry), *request.ethereum_nonce, *request.recipient_nonce,
            (*request.deadline).into(),
        ]
            .span(),
    )
}
pub fn revoke_hash(
    request: @RevokeRequest, statement: u256, chain: felt252, registry: ContractAddress,
) -> u256 {
    hash_words(
        array![
            hash_text(
                @"RevokeAssociation(string statement,address ethereumAddress,bytes32 currentAccountAddress,uint256 accountChainId,bytes32 registryAddress,uint256 ethereumNonce,uint64 deadline)",
            ),
            statement, ethereum_word(*request.ethereum_address),
            account_word(*request.current_account_address), chain.into(), account_word(registry),
            *request.ethereum_nonce, (*request.deadline).into(),
        ]
            .span(),
    )
}
