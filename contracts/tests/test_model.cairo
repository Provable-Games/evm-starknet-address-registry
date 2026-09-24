use contracts::interface::{IAddressRegistryDispatcher, IAddressRegistryDispatcherTrait};
use core::dict::{Felt252Dict, Felt252DictTrait};
use snforge_std::start_cheat_caller_address;
use crate::helpers::{deploy, eth, link, move_request, revoke_request};

#[test]
#[fuzzer]
fn seeded_state_machine(sequence: u128) {
    let registry = deploy('SN_SEPOLIA', 11155111, "Loot Survivor");
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let mut mapping: Felt252Dict<felt252> = Default::default();
    let mut nonces: Felt252Dict<felt252> = Default::default();
    let mut pairs: Felt252Dict<felt252> = Default::default();
    let ethereum_addresses = array![eth(1), eth(2), eth(3), eth(4)];
    let mut entropy = sequence;
    for step in 0..12_u32 {
        let key: u32 = (entropy % 4).try_into().unwrap() + 1;
        entropy /= 4;
        let destination: felt252 = (entropy % 3).into() + 1;
        entropy /= 3;
        let operation: u8 = (entropy % 4).try_into().unwrap();
        entropy /= 4;
        let old = mapping.get(key.into());
        let ethereum = *ethereum_addresses.at(key - 1);
        let account = destination.try_into().unwrap();
        if operation == 0 {
            if old == 0 {
                link(registry, key.into(), account);
                mapping.insert(key.into(), destination);
                nonces.insert(key.into(), nonces.get(key.into()) + 1);
                let pair = destination * 10 + key.into();
                pairs.insert(pair, pairs.get(pair) + 1);
            } else if old != destination {
                let (request, signature) = move_request(registry, key.into(), account);
                start_cheat_caller_address(registry, account);
                reader.move(request, signature);
                mapping.insert(key.into(), destination);
                nonces.insert(key.into(), nonces.get(key.into()) + 1);
                let previous_pair = old * 10 + key.into();
                let pair = destination * 10 + key.into();
                pairs.insert(previous_pair, pairs.get(previous_pair) + 1);
                pairs.insert(pair, pairs.get(pair) + 1);
            }
        } else if operation == 1 && old != 0 {
            start_cheat_caller_address(registry, old.try_into().unwrap());
            reader.unlink(ethereum);
            mapping.insert(key.into(), 0);
            nonces.insert(key.into(), nonces.get(key.into()) + 1);
            let pair = old * 10 + key.into();
            pairs.insert(pair, pairs.get(pair) + 1);
        } else if operation == 2 {
            let (request, signature) = revoke_request(registry, key.into());
            reader.revoke(request, signature);
            mapping.insert(key.into(), 0);
            nonces.insert(key.into(), nonces.get(key.into()) + 1);
            if old != 0 {
                let pair = old * 10 + key.into();
                pairs.insert(pair, pairs.get(pair) + 1);
            }
        } else {
            start_cheat_caller_address(registry, account);
            reader.invalidate_pending_incoming(ethereum);
            let pair = destination * 10 + key.into();
            pairs.insert(pair, pairs.get(pair) + 1);
        }
        // Independent model checks every wallet and every pair after each transition.
        for wallet in 1_u32..5 {
            let e = *ethereum_addresses.at(wallet - 1);
            let expected = mapping.get(wallet.into());
            let got: felt252 = reader.get_starknet_address(e).into();
            assert_model(got == expected, sequence, step);
            assert_model(
                reader.get_ethereum_nonce(e) == nonces.get(wallet.into()).into(), sequence, step,
            );
            for destination in 1_u32..4 {
                let value: felt252 = destination.into();
                let a = value.try_into().unwrap();
                assert_model(
                    reader.is_associated(e, a) == (expected == destination.into()), sequence, step,
                );
                let pair: felt252 = destination.into() * 10 + wallet.into();
                assert_model(
                    reader.get_recipient_nonce(a, e) == pairs.get(pair).into(), sequence, step,
                );
            };
        }
        for destination in 1_u32..4 {
            let value: felt252 = destination.into();
            let a = value.try_into().unwrap();
            let list = reader.get_ethereum_addresses(a, 0, 100);
            let mut expected_count = 0_u64;
            for wallet in 1_u32..5 {
                if mapping.get(wallet.into()) == destination.into() {
                    expected_count += 1;
                    let mut occurrences = 0_u32;
                    for item in list.span() {
                        if *item == *ethereum_addresses.at(wallet - 1) {
                            occurrences += 1;
                        }
                    }
                    assert_model(occurrences == 1, sequence, step);
                }
            }
            assert_model(reader.get_ethereum_address_count(a) == expected_count, sequence, step);
            assert_model(list.len().into() == expected_count, sequence, step);
        };
    };
}
fn assert_model(condition: bool, sequence: u128, step: u32) {
    assert!(condition, "state model mismatch sequence={} step={}", sequence, step);
}
