use contracts::interface::{
    IAddressRegistryDispatcher, IAddressRegistryDispatcherTrait, IAddressRegistrySafeDispatcher,
    IAddressRegistrySafeDispatcherTrait,
};
use snforge_std::cheatcodes::storage::{map_entry_address, store};
use snforge_std::{EventSpyTrait, spy_events, start_cheat_caller_address};
use crate::helpers::{deploy, eth, link, link_request, move_request, revoke_request};
const MAX: u256 = 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff;
fn set_nonce(
    registry: starknet::ContractAddress, selector: felt252, keys: Span<felt252>, value: u256,
) {
    let mut data = array![];
    Serde::serialize(@value, ref data);
    store(registry, map_entry_address(selector, keys), data.span());
}
#[test]
#[feature("safe_dispatcher")]
fn overflow_checks_precede_membership_writes() {
    let registry = deploy('SN_SEPOLIA', 11155111, "A");
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let safe = IAddressRegistrySafeDispatcher { contract_address: registry };
    let a = 111.try_into().unwrap();
    let b = 222.try_into().unwrap();
    let e = eth(1);
    let ef: felt252 = e.into();
    for case in 0..3_u32 {
        set_nonce(
            registry,
            selector!("ethereum_nonce"),
            array![ef].span(),
            if case == 0 {
                MAX
            } else {
                0
            },
        );
        set_nonce(
            registry,
            selector!("recipient_nonce"),
            array![111, ef].span(),
            if case == 1 {
                MAX
            } else {
                0
            },
        );
        store(
            registry,
            map_entry_address(selector!("ethereum_count"), array![111].span()),
            array![if case == 2 {
                18446744073709551615
            } else {
                0
            }].span(),
        );
        let (request, signature) = link_request(registry, 1, a);
        start_cheat_caller_address(registry, a);
        let mut spy = spy_events();
        let failure = safe.link(request, signature).unwrap_err();
        assert(
            *failure.at(0) == if case == 2 {
                'AR_COUNT_OVERFLOW'
            } else {
                'AR_NONCE_OVERFLOW'
            },
            'LINK_OVERFLOW',
        );
        assert(reader.get_starknet_address(e) == 0.try_into().unwrap(), 'NO_LINK');
        assert(spy.get_events().events.is_empty(), 'NO_EVENTS');
    }
    store(
        registry,
        map_entry_address(selector!("ethereum_count"), array![111].span()),
        array![0].span(),
    );
    link(registry, 1, a);
    set_nonce(registry, selector!("recipient_nonce"), array![111, ef].span(), MAX);
    let (request, signature) = move_request(registry, 1, b);
    start_cheat_caller_address(registry, b);
    assert(*safe.move(request, signature).unwrap_err().at(0) == 'AR_NONCE_OVERFLOW', 'OLD_PAIR');
    let (request, signature) = revoke_request(registry, 1);
    assert(
        *safe.revoke(request, signature).unwrap_err().at(0) == 'AR_NONCE_OVERFLOW', 'REVOKE_PAIR',
    );
    start_cheat_caller_address(registry, a);
    assert(*safe.unlink(e).unwrap_err().at(0) == 'AR_NONCE_OVERFLOW', 'UNLINK_PAIR');
    assert(
        *safe.invalidate_pending_incoming(e).unwrap_err().at(0) == 'AR_NONCE_OVERFLOW',
        'CANCEL_PAIR',
    );
    assert(reader.get_ethereum_addresses(a, 0, 100) == array![e], 'RETAIN_MEMBER');
    assert(reader.get_ethereum_address_count(b) == 0, 'NO_DEST');
    assert(reader.get_ethereum_nonce(e) == 1, 'RETAIN_NONCE');
}

#[test]
#[feature("safe_dispatcher")]
fn each_transition_overflow_rolls_back() {
    let registry = deploy('SN_MAIN', 1, "A");
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let safe = IAddressRegistrySafeDispatcher { contract_address: registry };
    let a = 111.try_into().unwrap();
    let b = 222.try_into().unwrap();
    link(registry, 1, a);
    let e = eth(1);
    let ef: felt252 = e.into();
    for case in 0..5_u32 {
        set_nonce(
            registry,
            selector!("ethereum_nonce"),
            array![ef].span(),
            if case < 3 {
                MAX
            } else {
                1
            },
        );
        set_nonce(
            registry,
            selector!("recipient_nonce"),
            array![222, ef].span(),
            if case == 3 {
                MAX
            } else {
                0
            },
        );
        store(
            registry,
            map_entry_address(selector!("ethereum_count"), array![222].span()),
            array![if case == 4 {
                18446744073709551615
            } else {
                0
            }].span(),
        );
        let mut spy = spy_events();
        let failure = if case == 0 {
            start_cheat_caller_address(registry, a);
            safe.unlink(e).unwrap_err()
        } else if case == 1 {
            let (request, signature) = revoke_request(registry, 1);
            safe.revoke(request, signature).unwrap_err()
        } else {
            let (request, signature) = move_request(registry, 1, b);
            start_cheat_caller_address(registry, b);
            safe.move(request, signature).unwrap_err()
        };
        assert(
            *failure.at(0) == if case == 4 {
                'AR_COUNT_OVERFLOW'
            } else {
                'AR_NONCE_OVERFLOW'
            },
            'ATOMIC_OVERFLOW',
        );
        assert(spy.get_events().events.is_empty(), 'ATOMIC_EVENTS');
        assert(reader.get_starknet_address(e) == a, 'ATOMIC_MAPPING');
        assert(reader.get_ethereum_addresses(a, 0, 100) == array![e], 'ATOMIC_REVERSE');
        assert(reader.get_recipient_nonce(a, e) == 1, 'ATOMIC_OLD_PAIR');
    };
}

#[test]
#[feature("safe_dispatcher")]
fn unlinked_revocation_nonce_overflow() {
    let registry = deploy('SN_MAIN', 1, "A");
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let safe = IAddressRegistrySafeDispatcher { contract_address: registry };
    let e = eth(1);
    let ef: felt252 = e.into();
    set_nonce(registry, selector!("ethereum_nonce"), array![ef].span(), MAX);
    let (request, signature) = revoke_request(registry, 1);
    let mut spy = spy_events();
    assert(
        *safe.revoke(request, signature).unwrap_err().at(0) == 'AR_NONCE_OVERFLOW',
        'UNLINKED_OVERFLOW',
    );
    assert(reader.get_ethereum_nonce(e) == MAX, 'RETAIN_MAXIMUM');
    assert(reader.get_starknet_address(e) == 0.try_into().unwrap(), 'RETAIN_UNLINKED');
    assert(spy.get_events().events.is_empty(), 'NO_OVERFLOW_EVENT');
}
