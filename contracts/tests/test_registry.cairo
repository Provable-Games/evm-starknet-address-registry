use contracts::interface::{IAddressRegistryDispatcher, IAddressRegistryDispatcherTrait};
use snforge_std::{EventSpyTrait, spy_events, start_cheat_caller_address};
use crate::helpers::{deploy, eth, link, move_request, revoke_request};
#[test]
fn lifecycle_and_enumeration() {
    let registry = deploy('SN_SEPOLIA', 11155111, "Loot Survivor");
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let a = 111.try_into().unwrap();
    let b = 222.try_into().unwrap();
    for key in 1_u32..5 {
        link(registry, key.into(), a);
    }
    assert(reader.get_ethereum_address_count(a) == 4, 'COUNT');
    assert(
        reader.get_ethereum_addresses(a, 0, 100) == array![eth(1), eth(2), eth(3), eth(4)], 'ORDER',
    );
    let (request, signature) = move_request(registry, 2, b);
    start_cheat_caller_address(registry, b);
    let mut spy = spy_events();
    reader.move(request, signature);
    assert(spy.get_events().events.len() == 4, 'MOVE_EVENTS');
    assert(reader.get_ethereum_addresses(a, 0, 100) == array![eth(1), eth(4), eth(3)], 'SWAP');
    assert(reader.get_ethereum_addresses(a, 1, 1) == array![eth(4)], 'OFFSET_MEMBER');
    assert(reader.get_ethereum_addresses(a, 1, 100) == array![eth(4), eth(3)], 'PARTIAL_PAGE');
    assert(reader.get_ethereum_addresses(a, 2, 2) == array![eth(3)], 'FINAL_PAGE');
    assert(reader.get_ethereum_addresses(a, 3, 1).is_empty(), 'OFFSET_COUNT');
    assert(reader.get_ethereum_addresses(a, 18446744073709551615, 1).is_empty(), 'MAX_OFFSET');
    start_cheat_caller_address(registry, a);
    reader.unlink(eth(1));
    assert(reader.get_ethereum_addresses(a, 0, 100) == array![eth(3), eth(4)], 'FIRST');
    reader.unlink(eth(4));
    assert(reader.get_ethereum_addresses(a, 0, 100) == array![eth(3)], 'LAST');
    let (request, signature) = revoke_request(registry, 3);
    reader.revoke(request, signature);
    let (request, signature) = revoke_request(registry, 3);
    reader.revoke(request, signature);
    assert(reader.get_ethereum_address_count(a) == 0, 'EMPTY');
    assert(reader.get_ethereum_nonce(eth(3)) == 3, 'REVOKE_NONCE');
    assert(reader.get_recipient_nonce(a, eth(3)) == 2, 'PAIR_NONCE');
    reader.invalidate_pending_incoming(eth(3));
    assert(reader.get_recipient_nonce(a, eth(3)) == 3, 'CANCEL');
    assert(reader.get_starknet_address(eth(2)) == b, 'UNRELATED');
    assert(reader.get_version() == '1', 'VERSION');
}
