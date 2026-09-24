//! Frozen public types and strict canonical signature serialization.
use starknet::{ContractAddress, EthAddress};

#[derive(Drop)]
pub struct Signature {
    pub r: u256,
    pub s: u256,
    pub y_parity: bool,
}

// Core BoolSerde accepts every nonzero felt as true. The frozen wire encoding is 0/1.
// Decode it explicitly before constructing the bool; do not change the public ABI.
pub impl SignatureSerde of Serde<Signature> {
    fn serialize(self: @Signature, ref output: Array<felt252>) {
        self.r.serialize(ref output);
        self.s.serialize(ref output);
        self.y_parity.serialize(ref output);
    }
    fn deserialize(ref serialized: Span<felt252>) -> Option<Signature> {
        let r = Serde::<u256>::deserialize(ref serialized)?;
        let s = Serde::<u256>::deserialize(ref serialized)?;
        let parity = *serialized.pop_front()?;
        if parity != 0 && parity != 1 {
            return None;
        }
        Some(Signature { r, s, y_parity: parity == 1 })
    }
}

#[derive(Drop, Serde)]
pub struct LinkRequest {
    pub ethereum_address: EthAddress,
    pub account_address: ContractAddress,
    pub ethereum_nonce: u256,
    pub recipient_nonce: u256,
    pub deadline: u64,
}

#[derive(Drop, Serde)]
pub struct MoveRequest {
    pub ethereum_address: EthAddress,
    pub account_address: ContractAddress,
    pub previous_account_address: ContractAddress,
    pub ethereum_nonce: u256,
    pub recipient_nonce: u256,
    pub deadline: u64,
}

#[derive(Drop, Serde)]
pub struct RevokeRequest {
    pub ethereum_address: EthAddress,
    pub current_account_address: ContractAddress,
    pub ethereum_nonce: u256,
    pub deadline: u64,
}

#[derive(Drop, Serde)]
pub struct SigningDomain {
    pub name: ByteArray,
    pub version: ByteArray,
    pub ethereum_chain_id: u256,
    pub account_chain_id: felt252,
    pub registry_address: ContractAddress,
    pub salt: u256,
    pub domain_separator: u256,
    pub account_label: ByteArray,
    pub link_statement: ByteArray,
    pub move_statement: ByteArray,
    pub revoke_statement: ByteArray,
    pub account_network_name: ByteArray,
}

#[starknet::interface]
pub trait IAddressRegistry<TContractState> {
    fn link(ref self: TContractState, request: LinkRequest, signature: Signature);
    fn move(ref self: TContractState, request: MoveRequest, signature: Signature);
    fn unlink(ref self: TContractState, ethereum_address: EthAddress);
    fn revoke(ref self: TContractState, request: RevokeRequest, signature: Signature);
    fn invalidate_pending_incoming(ref self: TContractState, ethereum_address: EthAddress);
    fn get_starknet_address(self: @TContractState, ethereum_address: EthAddress) -> ContractAddress;
    fn is_associated(
        self: @TContractState, ethereum_address: EthAddress, starknet_address: ContractAddress,
    ) -> bool;
    fn get_ethereum_address_count(self: @TContractState, starknet_address: ContractAddress) -> u64;
    fn get_ethereum_addresses(
        self: @TContractState, starknet_address: ContractAddress, offset: u64, limit: u32,
    ) -> Array<EthAddress>;
    fn get_ethereum_nonce(self: @TContractState, ethereum_address: EthAddress) -> u256;
    fn get_recipient_nonce(
        self: @TContractState, starknet_address: ContractAddress, ethereum_address: EthAddress,
    ) -> u256;
    fn get_signing_domain(self: @TContractState) -> SigningDomain;
    fn get_version(self: @TContractState) -> felt252;
}
