//! Test-only state seeding separates collection size from setup transaction costs.
use contracts::interface::{
    IAddressRegistryDispatcher, IAddressRegistryDispatcherTrait, IAddressRegistrySafeDispatcher,
    IAddressRegistrySafeDispatcherTrait,
};
use snforge_std::cheatcodes::storage::{map_entry_address, store};
use snforge_std::start_cheat_caller_address;
use starknet::ContractAddress;
use crate::helpers::{deploy, eth, link_request, move_request, revoke_request};
fn seed(registry: ContractAddress, account: felt252, size: u32, target: bool, position: u32) {
    store(
        registry,
        map_entry_address(selector!("ethereum_count"), array![account].span()),
        array![size.into()].span(),
    );
    for index in 0..size {
        let ethereum: felt252 = if target && index == position {
            eth(1).into()
        } else {
            0x10000 + account * 10000 + index.into()
        };
        store(
            registry,
            map_entry_address(
                selector!("ethereum_addresses"), array![account, index.into()].span(),
            ),
            array![ethereum].span(),
        );
        store(
            registry,
            map_entry_address(selector!("ethereum_index_plus_one"), array![ethereum].span()),
            array![(index + 1).into()].span(),
        );
        store(
            registry,
            map_entry_address(selector!("ethereum_to_starknet"), array![ethereum].span()),
            array![account].span(),
        );
    };
}
#[feature("safe_dispatcher")]
pub fn benchmark(operation: u8, size: u32, position: u32, label: ByteArray, limit: u32) {
    let registry = deploy('SN_SEPOLIA', 11155111, label);
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let safe = IAddressRegistrySafeDispatcher { contract_address: registry };
    let a = 111.try_into().unwrap();
    let b = 222.try_into().unwrap();
    seed(registry, 111, size, operation >= 1 && operation <= 3, position);
    if operation == 1 {
        seed(registry, 222, size, false, 0);
    }
    start_cheat_caller_address(registry, a);
    if operation >= 7 {
        if operation == 7 {
            let e: felt252 = eth(1).into();
            store(
                registry,
                map_entry_address(selector!("ethereum_nonce"), array![e].span()),
                array![0xffffffffffffffffffffffffffffffff, 0xffffffffffffffffffffffffffffffff]
                    .span(),
            );
        } else if operation == 8 {
            store(
                registry,
                map_entry_address(selector!("ethereum_count"), array![111].span()),
                array![18446744073709551615].span(),
            );
        }
        let (request, mut signature) = link_request(registry, 1, a);
        if operation == 9 {
            signature.r = 0;
        }
        let failure = safe.link(request, signature).unwrap_err();
        let expected = if operation == 7 {
            'AR_NONCE_OVERFLOW'
        } else if operation == 8 {
            'AR_COUNT_OVERFLOW'
        } else {
            'AR_BAD_SIGNATURE'
        };
        assert(*failure.at(0) == expected, 'RESOURCE_VALIDATION');
    } else if operation == 0 {
        let (request, signature) = link_request(registry, 1, a);
        reader.link(request, signature);
    } else if operation == 1 {
        let (request, signature) = move_request(registry, 1, b);
        start_cheat_caller_address(registry, b);
        reader.move(request, signature);
    } else if operation == 2 {
        reader.unlink(eth(1));
    } else if operation == 3 || operation == 4 {
        let (request, signature) = revoke_request(registry, 1);
        reader.revoke(request, signature);
    } else if operation == 5 {
        reader.invalidate_pending_incoming(eth(1));
    } else if limit == 0 || limit > 100 {
        let result = safe.get_ethereum_addresses(a, 0, limit);
        assert(*result.unwrap_err().at(0) == 'AR_BAD_PAGE_LIMIT', 'RESOURCE_REJECT');
    } else {
        let result = reader.get_ethereum_addresses(a, 0, limit);
        assert(result.len() == if size < limit {
            size
        } else {
            limit
        }, 'RESOURCE_PAGE');
    }
}
