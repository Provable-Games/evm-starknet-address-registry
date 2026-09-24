use contracts::eip712;
use contracts::interface::{
    IAddressRegistryDispatcher, IAddressRegistryDispatcherTrait, LinkRequest, MoveRequest,
    RevokeRequest, Signature,
};
use snforge_std::signature::secp256k1_curve::{
    Secp256k1CurveKeyPair, Secp256k1CurveKeyPairImpl, Secp256k1CurveSignerImpl,
};
use snforge_std::signature::{KeyPairTrait, SignerTrait};
use snforge_std::{
    ContractClassTrait, DeclareResultTrait, declare, start_cheat_block_timestamp_global,
    start_cheat_caller_address, start_cheat_chain_id_global,
};
use starknet::eth_signature::{is_eth_signature_valid, public_key_point_to_eth_address};
use starknet::secp256_trait::Signature as CoreSignature;
use starknet::{ContractAddress, EthAddress, SyscallResultTrait};

pub fn deploy(chain: felt252, ethereum_chain: u256, label: ByteArray) -> ContractAddress {
    start_cheat_chain_id_global(chain);
    start_cheat_block_timestamp_global(100);
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    let mut calldata = array![];
    Serde::serialize(@ethereum_chain, ref calldata);
    Serde::serialize(@label, ref calldata);
    let (address, _) = class.deploy(@calldata).unwrap_syscall();
    address
}
pub fn eth(key: u256) -> EthAddress {
    let pair: Secp256k1CurveKeyPair = KeyPairTrait::from_secret_key(key);
    public_key_point_to_eth_address(pair.public_key)
}
pub fn sign(key: u256, digest: u256) -> Signature {
    let pair: Secp256k1CurveKeyPair = KeyPairTrait::from_secret_key(key);
    let address = public_key_point_to_eth_address(pair.public_key);
    let (r, s) = pair.sign(digest).unwrap();
    let y_parity = !is_eth_signature_valid(digest, CoreSignature { r, s, y_parity: false }, address)
        .is_ok();
    assert(
        is_eth_signature_valid(digest, CoreSignature { r, s, y_parity }, address).is_ok(),
        'TEST_SIGNER',
    );
    Signature { r, s, y_parity }
}
pub fn link_request(
    registry: ContractAddress, key: u256, account: ContractAddress,
) -> (LinkRequest, Signature) {
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = eth(key);
    let request = LinkRequest {
        ethereum_address: ethereum,
        account_address: account,
        ethereum_nonce: reader.get_ethereum_nonce(ethereum),
        recipient_nonce: reader.get_recipient_nonce(account, ethereum),
        deadline: 1000,
    };
    let domain = reader.get_signing_domain();
    let message = eip712::link_hash(
        @request, eip712::hash_text(@domain.link_statement), domain.account_chain_id, registry,
    );
    let signature = sign(key, eip712::envelope(domain.domain_separator, message));
    (request, signature)
}
pub fn move_request(
    registry: ContractAddress, key: u256, account: ContractAddress,
) -> (MoveRequest, Signature) {
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = eth(key);
    let request = MoveRequest {
        ethereum_address: ethereum,
        account_address: account,
        previous_account_address: reader.get_starknet_address(ethereum),
        ethereum_nonce: reader.get_ethereum_nonce(ethereum),
        recipient_nonce: reader.get_recipient_nonce(account, ethereum),
        deadline: 1000,
    };
    let domain = reader.get_signing_domain();
    let message = eip712::move_hash(
        @request, eip712::hash_text(@domain.move_statement), domain.account_chain_id, registry,
    );
    let signature = sign(key, eip712::envelope(domain.domain_separator, message));
    (request, signature)
}
pub fn revoke_request(registry: ContractAddress, key: u256) -> (RevokeRequest, Signature) {
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let ethereum = eth(key);
    let request = RevokeRequest {
        ethereum_address: ethereum,
        current_account_address: reader.get_starknet_address(ethereum),
        ethereum_nonce: reader.get_ethereum_nonce(ethereum),
        deadline: 1000,
    };
    let domain = reader.get_signing_domain();
    let message = eip712::revoke_hash(
        @request, eip712::hash_text(@domain.revoke_statement), domain.account_chain_id, registry,
    );
    let signature = sign(key, eip712::envelope(domain.domain_separator, message));
    (request, signature)
}
pub fn link(registry: ContractAddress, key: u256, account: ContractAddress) {
    let (request, signature) = link_request(registry, key, account);
    start_cheat_caller_address(registry, account);
    IAddressRegistryDispatcher { contract_address: registry }.link(request, signature);
}
