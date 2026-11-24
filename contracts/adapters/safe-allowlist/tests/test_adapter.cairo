use safe_allowlist::{IAssociationLookupDispatcher, IAssociationLookupDispatcherTrait};
use snforge_std::{ContractClassTrait, DeclareResultTrait, declare};

#[starknet::contract]
mod RegistryFixture {
    use starknet::{ContractAddress, EthAddress};

    #[storage]
    struct Storage {}

    #[abi(embed_v0)]
    impl Lookup of safe_allowlist::IAssociationLookup<ContractState> {
        fn is_associated(
            self: @ContractState, ethereum_address: EthAddress, starknet_address: ContractAddress,
        ) -> bool {
            let linked_first = ethereum_address == 11.try_into().unwrap()
                && starknet_address == 101.try_into().unwrap();
            let linked_second = ethereum_address == 22.try_into().unwrap()
                && starknet_address == 202.try_into().unwrap();
            linked_first || linked_second
        }
    }
}

#[test]
fn allowlist_intersects_current_registry_links() {
    let (registry, _) = declare("RegistryFixture")
        .unwrap()
        .contract_class()
        .deploy(@array![])
        .unwrap();
    let class = declare("SafeAllowlistAdapter").unwrap().contract_class();
    let (adapter, _) = class.deploy(@array![registry.into(), 2, 33, 11]).unwrap();
    let adapter = IAssociationLookupDispatcher { contract_address: adapter };
    let registry = IAssociationLookupDispatcher { contract_address: registry };
    let first = 11.try_into().unwrap();
    let second = 22.try_into().unwrap();
    let third = 33.try_into().unwrap();
    let account = 101.try_into().unwrap();
    let other = 202.try_into().unwrap();

    assert(adapter.is_associated(first, account), 'ADMITTED_LINK');
    assert(!adapter.is_associated(first, other), 'WRONG_DESTINATION');
    assert(!adapter.is_associated(third, account), 'ADMITTED_WITHOUT_LINK');
    assert(registry.is_associated(second, other), 'UPSTREAM_LINK');
    assert(!adapter.is_associated(second, other), 'NOT_ADMITTED');
}

#[test]
fn invalid_constructor_addresses_revert() {
    let class = declare("SafeAllowlistAdapter").unwrap().contract_class();
    let zero_registry = class.deploy(@array![0, 1, 11]).unwrap_err();
    assert(*zero_registry.at(0) == 'ZERO_REGISTRY', 'EXPECTED_ZERO_REGISTRY');
    let zero_safe = class.deploy(@array![123, 2, 11, 0]).unwrap_err();
    assert(*zero_safe.at(0) == 'ZERO_SAFE', 'EXPECTED_ZERO_SAFE');
}
