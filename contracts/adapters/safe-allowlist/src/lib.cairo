use starknet::{ContractAddress, EthAddress};

#[starknet::interface]
pub trait IAssociationLookup<TContractState> {
    fn is_associated(
        self: @TContractState, ethereum_address: EthAddress, starknet_address: ContractAddress,
    ) -> bool;
}

#[starknet::contract]
pub mod SafeAllowlistAdapter {
    use core::num::traits::Zero;
    use starknet::storage::{
        Map, StorageMapReadAccess, StorageMapWriteAccess, StoragePointerReadAccess,
        StoragePointerWriteAccess,
    };
    use starknet::{ContractAddress, EthAddress};
    use super::{IAssociationLookupDispatcher, IAssociationLookupDispatcherTrait};

    #[storage]
    struct Storage {
        registry: ContractAddress,
        admitted: Map<EthAddress, bool>,
    }

    #[constructor]
    fn constructor(ref self: ContractState, registry: ContractAddress, safes: Span<EthAddress>) {
        assert(!registry.is_zero(), 'ZERO_REGISTRY');
        self.registry.write(registry);
        for safe in safes {
            assert(!safe.is_zero(), 'ZERO_SAFE');
            self.admitted.write(*safe, true);
        }
    }

    #[abi(embed_v0)]
    impl Lookup of super::IAssociationLookup<ContractState> {
        fn is_associated(
            self: @ContractState, ethereum_address: EthAddress, starknet_address: ContractAddress,
        ) -> bool {
            self.admitted.read(ethereum_address)
                && IAssociationLookupDispatcher { contract_address: self.registry.read() }
                    .is_associated(ethereum_address, starknet_address)
        }
    }
}
