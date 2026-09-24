use contracts::interface::{
    IAddressRegistryDispatcher, IAddressRegistryDispatcherTrait, IAddressRegistrySafeDispatcher,
    IAddressRegistrySafeDispatcherTrait,
};
use snforge_std::{
    EventSpyTrait, spy_events, start_cheat_block_timestamp, start_cheat_caller_address,
};
use crate::helpers::{deploy, eth, link, link_request, move_request, revoke_request, sign};

#[test]
#[feature("safe_dispatcher")]
fn rejected_links_are_atomic() {
    let registry = deploy('SN_SEPOLIA', 11155111, "Loot Survivor");
    let safe = IAddressRegistrySafeDispatcher { contract_address: registry };
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let account = 111.try_into().unwrap();
    for case in 0..12_u32 {
        start_cheat_caller_address(registry, account);
        start_cheat_block_timestamp(registry, 100);
        let (mut request, mut signature) = link_request(registry, 1, account);
        let expected = match case {
            0 => {
                request.ethereum_address = 0.try_into().unwrap();
                'AR_ZERO_ADDRESS'
            },
            1 => {
                request.account_address = 0.try_into().unwrap();
                'AR_ZERO_ADDRESS'
            },
            2 => {
                start_cheat_caller_address(registry, 222.try_into().unwrap());
                'AR_BAD_CALLER'
            },
            3 => {
                request.ethereum_nonce = 1;
                'AR_STALE_ETH_NONCE'
            },
            4 => {
                request.recipient_nonce = 1;
                'AR_STALE_RECIP_NONCE'
            },
            5 => {
                request.deadline = 0;
                'AR_BAD_DEADLINE'
            },
            6 => {
                start_cheat_block_timestamp(registry, 1001);
                'AR_EXPIRED'
            },
            7 => {
                signature.r = 0;
                'AR_BAD_SIGNATURE'
            },
            8 => {
                signature.s = 0;
                'AR_BAD_SIGNATURE'
            },
            9 => {
                signature.s = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141
                    - signature.s;
                signature.y_parity = !signature.y_parity;
                'AR_BAD_SIGNATURE'
            },
            10 => {
                signature.y_parity = !signature.y_parity;
                'AR_BAD_SIGNATURE'
            },
            _ => {
                signature = sign(2, 123);
                'AR_BAD_SIGNATURE'
            },
        };
        let mut spy = spy_events();
        let failure = safe.link(request, signature).unwrap_err();
        assert(failure == array![expected, 'ENTRYPOINT_FAILED'], 'WRONG_LINK_ERROR');
        assert(spy.get_events().events.is_empty(), 'REVERT_EVENTS');
        assert(reader.get_ethereum_address_count(account) == 0, 'REVERT_COUNT');
        assert(reader.get_starknet_address(eth(1)) == 0.try_into().unwrap(), 'REVERT_MAPPING');
        assert(reader.get_ethereum_nonce(eth(1)) == 0, 'REVERT_NONCE');
        assert(reader.get_recipient_nonce(account, eth(1)) == 0, 'REVERT_PAIR');
    };
}

#[test]
#[feature("safe_dispatcher")]
fn state_caller_previous_and_replay_rejections() {
    let registry = deploy('SN_MAIN', 1, "A");
    let safe = IAddressRegistrySafeDispatcher { contract_address: registry };
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let a = 111.try_into().unwrap();
    let b = 222.try_into().unwrap();
    let zero = 0.try_into().unwrap();
    let failure = safe.unlink(eth(1)).unwrap_err();
    assert(failure == array!['AR_NOT_LINKED', 'ENTRYPOINT_FAILED'], 'ABSENT');
    assert(
        safe.unlink(zero).unwrap_err() == array!['AR_ZERO_ADDRESS', 'ENTRYPOINT_FAILED'], 'ZERO',
    );
    start_cheat_caller_address(registry, 0.try_into().unwrap());
    assert(
        safe
            .invalidate_pending_incoming(eth(1))
            .unwrap_err() == array!['AR_ZERO_ADDRESS', 'ENTRYPOINT_FAILED'],
        'ZERO_CALLER',
    );
    start_cheat_caller_address(registry, a);
    assert(
        safe
            .invalidate_pending_incoming(zero)
            .unwrap_err() == array!['AR_ZERO_ADDRESS', 'ENTRYPOINT_FAILED'],
        'ZERO_ETH',
    );
    let (mut movement, signature) = move_request(registry, 1, b);
    movement.previous_account_address = a;
    start_cheat_caller_address(registry, b);
    assert(
        safe.move(movement, signature).unwrap_err() == array!['AR_NOT_LINKED', 'ENTRYPOINT_FAILED'],
        'MOVE_ABSENT',
    );
    link(registry, 1, a);
    let (request, signature) = link_request(registry, 1, a);
    assert(
        safe
            .link(request, signature)
            .unwrap_err() == array!['AR_ALREADY_LINKED', 'ENTRYPOINT_FAILED'],
        'LINK_EXISTING',
    );
    start_cheat_caller_address(registry, b);
    assert(
        safe.unlink(eth(1)).unwrap_err() == array!['AR_BAD_CALLER', 'ENTRYPOINT_FAILED'],
        'UNLINK_CALLER',
    );
    let (mut movement, signature) = move_request(registry, 1, b);
    movement.previous_account_address = 333.try_into().unwrap();
    assert(
        safe
            .move(movement, signature)
            .unwrap_err() == array!['AR_BAD_PREVIOUS_ACCOUNT', 'ENTRYPOINT_FAILED'],
        'PREVIOUS',
    );
    let (mut movement, signature) = move_request(registry, 1, b);
    movement.previous_account_address = 0.try_into().unwrap();
    assert(
        safe
            .move(movement, signature)
            .unwrap_err() == array!['AR_ZERO_ADDRESS', 'ENTRYPOINT_FAILED'],
        'PREVIOUS_ZERO',
    );
    let (movement, signature) = move_request(registry, 1, a);
    start_cheat_caller_address(registry, a);
    assert(
        safe
            .move(movement, signature)
            .unwrap_err() == array!['AR_SAME_ACCOUNT', 'ENTRYPOINT_FAILED'],
        'SAME',
    );
    let (mut revocation, signature) = revoke_request(registry, 1);
    revocation.current_account_address = b;
    assert(
        safe
            .revoke(revocation, signature)
            .unwrap_err() == array!['AR_BAD_CURRENT_ACCOUNT', 'ENTRYPOINT_FAILED'],
        'CURRENT',
    );
    let (stale_revoke, stale_signature) = revoke_request(registry, 1);
    let (movement, signature) = move_request(registry, 1, b);
    start_cheat_caller_address(registry, b);
    reader.move(movement, signature);
    assert(
        safe
            .revoke(stale_revoke, stale_signature)
            .unwrap_err() == array!['AR_STALE_ETH_NONCE', 'ENTRYPOINT_FAILED'],
        'RACE',
    );
    let (movement, signature) = move_request(registry, 1, a);
    start_cheat_caller_address(registry, a);
    reader.move(movement, signature);
    assert(reader.get_ethereum_nonce(eth(1)) == 3, 'RETURN_NONCE');
    assert(reader.get_recipient_nonce(a, eth(1)) == 3, 'RETURN_PAIR');
    for limit in array![0_u32, 101].span() {
        assert(
            safe
                .get_ethereum_addresses(a, 0, *limit)
                .unwrap_err() == array!['AR_BAD_PAGE_LIMIT', 'ENTRYPOINT_FAILED'],
            'PAGE',
        );
        assert(
            safe
                .get_ethereum_addresses(0.try_into().unwrap(), 0, *limit)
                .unwrap_err() == array!['AR_BAD_PAGE_LIMIT', 'ENTRYPOINT_FAILED'],
            'ZERO_PAGE',
        );
    }
    assert(reader.get_starknet_address(zero) == 0.try_into().unwrap(), 'ZERO_VIEW');
    assert(!reader.is_associated(zero, a), 'ZERO_MEMBER');
    assert(!reader.is_associated(eth(1), 0.try_into().unwrap()), 'ZERO_ACCOUNT');
    assert(reader.get_ethereum_nonce(zero) == 0, 'ZERO_NONCE');
    assert(reader.get_recipient_nonce(0.try_into().unwrap(), eth(1)) == 0, 'ZERO_PAIR');
    assert(reader.get_ethereum_address_count(0.try_into().unwrap()) == 0, 'ZERO_COUNT');
}

// Capture every fixture wallet/account pair, both reverse lists and all nonces.
fn authorization_snapshot(reader: IAddressRegistryDispatcher) -> Array<felt252> {
    let mut snapshot = array![];
    for key in 1..5_u32 {
        let ethereum = eth(key.into());
        Serde::serialize(@reader.get_starknet_address(ethereum), ref snapshot);
        Serde::serialize(@reader.get_ethereum_nonce(ethereum), ref snapshot);
        for account in array![111, 222, 333].span() {
            let account = (*account).try_into().unwrap();
            Serde::serialize(@reader.get_recipient_nonce(account, ethereum), ref snapshot);
            Serde::serialize(@reader.is_associated(ethereum, account), ref snapshot);
        };
    }
    for account in array![111, 222, 333].span() {
        let account = (*account).try_into().unwrap();
        Serde::serialize(@reader.get_ethereum_address_count(account), ref snapshot);
        Serde::serialize(@reader.get_ethereum_addresses(account, 0, 100), ref snapshot);
    }
    snapshot
}

#[feature("safe_dispatcher")]
fn isolated_authorization_rejection(case: u32) {
    let registry = deploy('SN_MAIN', 1, "A");
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let safe = IAddressRegistrySafeDispatcher { contract_address: registry };
    let a = 111.try_into().unwrap();
    let b = 222.try_into().unwrap();
    let relayer = 333.try_into().unwrap();
    link(registry, 1, a);
    link(registry, 2, a);
    link(registry, 3, b);
    // Exercise nonzero current destination and Ethereum nonces, including an
    // unlinked wallet with an earlier successful revocation.
    start_cheat_caller_address(registry, b);
    reader.invalidate_pending_incoming(eth(1));
    reader.invalidate_pending_incoming(eth(4));
    let (request, signature) = revoke_request(registry, 4);
    reader.revoke(request, signature);
    let before = authorization_snapshot(reader);
    let mut spy = spy_events();
    let expected = if case == 1 {
        'AR_BAD_CALLER'
    } else {
        'AR_BAD_SIGNATURE'
    };
    let failure = if case < 2 {
        let (request, mut signature) = move_request(registry, 1, b);
        if case == 0 {
            signature.r = 0;
            start_cheat_caller_address(registry, b);
        } else {
            // The request and signature are valid; only the immediate caller differs.
            start_cheat_caller_address(registry, relayer);
        }
        safe.move(request, signature).unwrap_err()
    } else {
        let key = if case == 2 {
            1
        } else {
            4
        };
        let (request, mut signature) = revoke_request(registry, key);
        signature.r = 0;
        start_cheat_caller_address(registry, relayer);
        safe.revoke(request, signature).unwrap_err()
    };
    assert(failure == array![expected, 'ENTRYPOINT_FAILED'], 'AUTH_ERROR');
    assert(spy.get_events().events.is_empty(), 'AUTH_EVENTS');
    assert(authorization_snapshot(reader) == before, 'AUTH_STATE');
}

#[test]
fn move_invalid_signature_preserves_state() {
    isolated_authorization_rejection(0);
}

#[test]
fn move_valid_signature_wrong_caller_preserves_state() {
    isolated_authorization_rejection(1);
}

#[test]
fn linked_revoke_invalid_signature_preserves_state() {
    isolated_authorization_rejection(2);
}

#[test]
fn unlinked_revoke_invalid_signature_preserves_state() {
    isolated_authorization_rejection(3);
}
