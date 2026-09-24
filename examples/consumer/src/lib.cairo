use starknet::{ContractAddress, EthAddress};

#[starknet::interface]
pub trait IRegistry<TContractState> {
    fn is_associated(
        self: @TContractState, ethereum_address: EthAddress, starknet_address: ContractAddress,
    ) -> bool;
}

#[starknet::interface]
pub trait IConsumer<TContractState> {
    fn act(ref self: TContractState, candidate: EthAddress);
    fn accepted(self: @TContractState) -> u64;
}

// The registry answers association only; this consumer owns its own policy.
#[starknet::contract]
pub mod AssociationConsumer {
    use core::num::traits::Zero;
    use starknet::storage::{
        Map, StorageMapReadAccess, StorageMapWriteAccess, StoragePointerReadAccess,
        StoragePointerWriteAccess,
    };
    use starknet::{ContractAddress, EthAddress, get_caller_address};
    use super::{IRegistryDispatcher, IRegistryDispatcherTrait};

    #[storage]
    struct Storage {
        registry: ContractAddress,
        allowed: Map<EthAddress, bool>,
        accepted: u64,
    }

    #[constructor]
    fn constructor(ref self: ContractState, registry: ContractAddress, allowed: Span<EthAddress>) {
        assert(!registry.is_zero(), 'CONSUMER_ZERO_REGISTRY');
        self.registry.write(registry);
        for candidate in allowed {
            assert(!candidate.is_zero(), 'CONSUMER_ZERO_CANDIDATE');
            self.allowed.write(*candidate, true);
        }
    }

    #[abi(embed_v0)]
    impl Consumer of super::IConsumer<ContractState> {
        fn act(ref self: ContractState, candidate: EthAddress) {
            let caller = get_caller_address();
            assert(!caller.is_zero(), 'CONSUMER_ZERO_CALLER');
            assert(!candidate.is_zero(), 'CONSUMER_ZERO_CANDIDATE');
            assert(self.allowed.read(candidate), 'CONSUMER_NOT_ALLOWED');
            let registry = IRegistryDispatcher { contract_address: self.registry.read() };
            assert(registry.is_associated(candidate, caller), 'CONSUMER_NOT_ASSOCIATED');
            self.accepted.write(self.accepted.read() + 1);
        }
        fn accepted(self: @ContractState) -> u64 {
            self.accepted.read()
        }
    }
}

#[starknet::interface]
pub trait IForwarder<TContractState> {
    fn forward(ref self: TContractState, consumer: ContractAddress, candidate: EthAddress);
}

// Negative fixture: forwarding changes the consumer's immediate caller.
#[starknet::contract]
pub mod ConsumerForwarder {
    use starknet::{ContractAddress, EthAddress};
    use super::{IConsumerDispatcher, IConsumerDispatcherTrait};
    #[storage]
    struct Storage {}
    #[abi(embed_v0)]
    impl Forwarder of super::IForwarder<ContractState> {
        fn forward(ref self: ContractState, consumer: ContractAddress, candidate: EthAddress) {
            IConsumerDispatcher { contract_address: consumer }.act(candidate);
        }
    }
}
