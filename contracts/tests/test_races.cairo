use contracts::eip712;
use contracts::interface::{
    IAddressRegistryDispatcher, IAddressRegistryDispatcherTrait, IAddressRegistrySafeDispatcher,
    IAddressRegistrySafeDispatcherTrait,
};
use snforge_std::{start_cheat_block_timestamp, start_cheat_caller_address};
use crate::helpers::{deploy, eth, link, link_request, move_request, revoke_request, sign};
#[test]
#[feature("safe_dispatcher")]
fn future_nonce_and_destination_cancellation() {
    let registry = deploy('SN_SEPOLIA', 11155111, "A");
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let safe = IAddressRegistrySafeDispatcher { contract_address: registry };
    let a = 111.try_into().unwrap();
    let b = 222.try_into().unwrap();
    let (mut future, _) = link_request(registry, 1, a);
    future.recipient_nonce = 1;
    let domain = reader.get_signing_domain();
    let digest = eip712::envelope(
        domain.domain_separator,
        eip712::link_hash(
            @future, eip712::hash_text(@domain.link_statement), domain.account_chain_id, registry,
        ),
    );
    let future_signature = sign(1, digest);
    start_cheat_caller_address(registry, a);
    reader.invalidate_pending_incoming(eth(1));
    // Deliberately signed future pair nonce becomes valid: cancellation is not permanent opt-out.
    reader.link(future, future_signature);
    let (movement, signature) = move_request(registry, 1, b);
    reader.invalidate_pending_incoming(eth(1));
    start_cheat_caller_address(registry, b);
    reader.move(movement, signature);
    let (movement, signature) = move_request(registry, 1, a);
    start_cheat_caller_address(registry, a);
    reader.invalidate_pending_incoming(eth(1));
    assert(
        *safe.move(movement, signature).unwrap_err().at(0) == 'AR_STALE_RECIP_NONCE', 'DEST_CANCEL',
    );
    assert(reader.get_starknet_address(eth(1)) == b, 'PRESERVE_LINK');
    let (stale, stale_sig) = link_request(registry, 2, a);
    link(registry, 2, a);
    reader.unlink(eth(2));
    assert(
        *safe.link(stale, stale_sig).unwrap_err().at(0) == 'AR_STALE_ETH_NONCE', 'RETURN_REPLAY',
    );
}
#[test]
fn deadline_equality_and_maximum() {
    let registry = deploy('SN_MAIN', 1, "A");
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let a = 111.try_into().unwrap();
    for key in 1_u32..3 {
        let (mut request, _) = link_request(registry, key.into(), a);
        request.deadline = if key == 1 {
            100
        } else {
            18446744073709551615
        };
        start_cheat_block_timestamp(registry, request.deadline);
        let domain = reader.get_signing_domain();
        let digest = eip712::envelope(
            domain.domain_separator,
            eip712::link_hash(
                @request,
                eip712::hash_text(@domain.link_statement),
                domain.account_chain_id,
                registry,
            ),
        );
        start_cheat_caller_address(registry, a);
        reader.link(request, sign(key.into(), digest));
    }
    assert(reader.get_ethereum_address_count(a) == 2, 'BOUNDARY_DEADLINES');
}

#[test]
#[feature("safe_dispatcher")]
fn future_ethereum_nonce_and_unlink_move_race() {
    let registry = deploy('SN_MAIN', 1, "A");
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let safe = IAddressRegistrySafeDispatcher { contract_address: registry };
    let a = 111.try_into().unwrap();
    let b = 222.try_into().unwrap();
    let (mut future, _) = link_request(registry, 1, a);
    future.ethereum_nonce = 1;
    let domain = reader.get_signing_domain();
    let digest = eip712::envelope(
        domain.domain_separator,
        eip712::link_hash(
            @future, eip712::hash_text(@domain.link_statement), domain.account_chain_id, registry,
        ),
    );
    start_cheat_caller_address(registry, a);
    let mut encoded = array![];
    Serde::serialize(@future, ref encoded);
    let future_signature = sign(1, digest);
    Serde::serialize(@future_signature, ref encoded);
    assert(
        starknet::syscalls::call_contract_syscall(registry, selector!("link"), encoded.span())
            .is_err(),
        'FUTURE_NOT_YET',
    );
    let (revocation, signature) = revoke_request(registry, 1);
    reader.revoke(revocation, signature);
    reader.link(future, future_signature);
    let (movement, signature) = move_request(registry, 1, b);
    reader.unlink(eth(1));
    start_cheat_caller_address(registry, b);
    assert(
        *safe.move(movement, signature).unwrap_err().at(0) == 'AR_STALE_ETH_NONCE', 'UNLINK_WINS',
    );
    assert(reader.get_ethereum_address_count(a) == 0, 'OLD_EMPTY');
    assert(reader.get_ethereum_address_count(b) == 0, 'NEW_EMPTY');
    assert(reader.get_ethereum_nonce(eth(1)) == 3, 'RACE_NONCE');
}
