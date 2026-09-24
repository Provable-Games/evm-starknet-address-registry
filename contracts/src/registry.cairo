//! Immutable generic Ethereum address association registry.
#[starknet::contract]
pub mod EthereumAddressAssociationRegistry {
    use core::num::traits::Zero;
    use starknet::storage::{
        Map, StorageMapReadAccess, StorageMapWriteAccess, StoragePointerReadAccess,
        StoragePointerWriteAccess,
    };
    use starknet::{
        ContractAddress, EthAddress, get_block_timestamp, get_caller_address, get_contract_address,
        get_tx_info,
    };
    use crate::interface::{LinkRequest, MoveRequest, RevokeRequest, Signature, SigningDomain};
    use crate::{eip712, labels, signature, state};
    #[storage]
    struct Storage {
        ethereum_to_starknet: Map<EthAddress, ContractAddress>,
        ethereum_addresses: Map<(ContractAddress, u64), EthAddress>,
        ethereum_count: Map<ContractAddress, u64>,
        ethereum_index_plus_one: Map<EthAddress, u64>,
        ethereum_nonce: Map<EthAddress, u256>,
        recipient_nonce: Map<(ContractAddress, EthAddress), u256>,
        ethereum_chain_id: u256,
        account_label: ByteArray,
        domain_separator: u256,
        domain_salt: u256,
        link_statement_hash: u256,
        move_statement_hash: u256,
        revoke_statement_hash: u256,
    }
    #[event]
    #[derive(Drop, starknet::Event)]
    pub enum Event {
        AssociationChanged: AssociationChanged,
        EthereumNonceAdvanced: EthereumNonceAdvanced,
        RecipientNonceAdvanced: RecipientNonceAdvanced,
    }

    #[derive(Drop, starknet::Event)]
    pub struct AssociationChanged {
        #[key]
        pub ethereum_address: EthAddress,
        pub previous_starknet_address: ContractAddress,
        pub new_starknet_address: ContractAddress,
        pub operation: u8,
    }

    #[derive(Drop, starknet::Event)]
    pub struct EthereumNonceAdvanced {
        #[key]
        pub ethereum_address: EthAddress,
        pub new_nonce: u256,
    }

    #[derive(Drop, starknet::Event)]
    pub struct RecipientNonceAdvanced {
        #[key]
        pub starknet_address: ContractAddress,
        #[key]
        pub ethereum_address: EthAddress,
        pub new_nonce: u256,
    }

    #[constructor]
    fn constructor(ref self: ContractState, ethereum_chain_id: u256, account_label: ByteArray) {
        let chain = get_tx_info().chain_id;
        assert(
            (chain == 'SN_MAIN' && ethereum_chain_id == 1)
                || (chain == 'SN_SEPOLIA' && ethereum_chain_id == 11155111),
            'AR_BAD_CHAIN_PAIR',
        );
        labels::validate(@account_label);
        let (link, movement, revoke) = labels::statements(@account_label);
        let salt = eip712::salt(chain, get_contract_address());
        self.ethereum_chain_id.write(ethereum_chain_id);
        self.account_label.write(account_label);
        self.domain_salt.write(salt);
        self.domain_separator.write(eip712::domain(ethereum_chain_id, salt));
        self.link_statement_hash.write(eip712::hash_text(@link));
        self.move_statement_hash.write(eip712::hash_text(@movement));
        self.revoke_statement_hash.write(eip712::hash_text(@revoke));
    }

    #[generate_trait]
    impl Internal of InternalTrait {
        fn check_signed(self: @ContractState, ethereum: EthAddress, nonce: u256, deadline: u64) {
            assert(!ethereum.is_zero(), 'AR_ZERO_ADDRESS');
            assert(deadline != 0, 'AR_BAD_DEADLINE');
            assert(get_block_timestamp() <= deadline, 'AR_EXPIRED');
            assert(self.ethereum_nonce.read(ethereum) == nonce, 'AR_STALE_ETH_NONCE');
        }
        fn check_recipient(
            self: @ContractState, ethereum: EthAddress, account: ContractAddress, nonce: u256,
        ) {
            assert(!account.is_zero(), 'AR_ZERO_ADDRESS');
            assert(get_caller_address() == account, 'AR_BAD_CALLER');
            assert(self.recipient_nonce.read((account, ethereum)) == nonce, 'AR_STALE_RECIP_NONCE');
        }
        fn insert(
            ref self: ContractState, ethereum: EthAddress, account: ContractAddress, count: u64,
        ) {
            // The increment was checked before any writes.
            self.ethereum_addresses.write((account, count - 1), ethereum);
            self.ethereum_index_plus_one.write(ethereum, count);
            self.ethereum_count.write(account, count);
            self.ethereum_to_starknet.write(ethereum, account);
        }
        fn remove(ref self: ContractState, ethereum: EthAddress, account: ContractAddress) {
            let last = self.ethereum_count.read(account) - 1;
            let index = self.ethereum_index_plus_one.read(ethereum) - 1;
            if index != last {
                let replacement = self.ethereum_addresses.read((account, last));
                self.ethereum_addresses.write((account, index), replacement);
                self.ethereum_index_plus_one.write(replacement, index + 1);
            }
            self.ethereum_addresses.write((account, last), 0.try_into().unwrap());
            self.ethereum_count.write(account, last);
            self.ethereum_index_plus_one.write(ethereum, 0);
            self.ethereum_to_starknet.write(ethereum, 0.try_into().unwrap());
        }
        fn advance_ethereum(ref self: ContractState, ethereum: EthAddress, nonce: u256) {
            self.ethereum_nonce.write(ethereum, nonce);
            self.emit(EthereumNonceAdvanced { ethereum_address: ethereum, new_nonce: nonce });
        }
        fn advance_recipient(
            ref self: ContractState, ethereum: EthAddress, account: ContractAddress, nonce: u256,
        ) {
            self.recipient_nonce.write((account, ethereum), nonce);
            self
                .emit(
                    RecipientNonceAdvanced {
                        starknet_address: account, ethereum_address: ethereum, new_nonce: nonce,
                    },
                );
        }
    }

    #[abi(embed_v0)]
    impl AddressRegistry of crate::interface::IAddressRegistry<ContractState> {
        fn link(ref self: ContractState, request: LinkRequest, signature: Signature) {
            let ethereum = request.ethereum_address;
            let account = request.account_address;
            self.check_signed(ethereum, request.ethereum_nonce, request.deadline);
            self.check_recipient(ethereum, account, request.recipient_nonce);
            assert(self.ethereum_to_starknet.read(ethereum).is_zero(), 'AR_ALREADY_LINKED');
            let message = eip712::link_hash(
                @request,
                self.link_statement_hash.read(),
                get_tx_info().chain_id,
                get_contract_address(),
            );
            signature::verify(
                eip712::envelope(self.domain_separator.read(), message), signature, ethereum,
            );
            let nonce = state::next_nonce(request.ethereum_nonce);
            let recipient = state::next_nonce(request.recipient_nonce);
            let count = state::next_count(self.ethereum_count.read(account));
            self.insert(ethereum, account, count);
            self
                .emit(
                    AssociationChanged {
                        ethereum_address: ethereum,
                        previous_starknet_address: 0.try_into().unwrap(),
                        new_starknet_address: account,
                        operation: 1,
                    },
                );
            self.advance_ethereum(ethereum, nonce);
            self.advance_recipient(ethereum, account, recipient);
        }
        fn move(ref self: ContractState, request: MoveRequest, signature: Signature) {
            let ethereum = request.ethereum_address;
            let account = request.account_address;
            let previous = request.previous_account_address;
            self.check_signed(ethereum, request.ethereum_nonce, request.deadline);
            self.check_recipient(ethereum, account, request.recipient_nonce);
            assert(!previous.is_zero(), 'AR_ZERO_ADDRESS');
            let current = self.ethereum_to_starknet.read(ethereum);
            assert(!current.is_zero(), 'AR_NOT_LINKED');
            assert(current == previous, 'AR_BAD_PREVIOUS_ACCOUNT');
            assert(previous != account, 'AR_SAME_ACCOUNT');
            let message = eip712::move_hash(
                @request,
                self.move_statement_hash.read(),
                get_tx_info().chain_id,
                get_contract_address(),
            );
            signature::verify(
                eip712::envelope(self.domain_separator.read(), message), signature, ethereum,
            );
            let nonce = state::next_nonce(request.ethereum_nonce);
            let old_recipient = state::next_nonce(self.recipient_nonce.read((previous, ethereum)));
            let recipient = state::next_nonce(request.recipient_nonce);
            let count = state::next_count(self.ethereum_count.read(account));
            self.remove(ethereum, previous);
            self.insert(ethereum, account, count);
            self
                .emit(
                    AssociationChanged {
                        ethereum_address: ethereum,
                        previous_starknet_address: previous,
                        new_starknet_address: account,
                        operation: 2,
                    },
                );
            self.advance_ethereum(ethereum, nonce);
            self.advance_recipient(ethereum, previous, old_recipient);
            self.advance_recipient(ethereum, account, recipient);
        }
        fn unlink(ref self: ContractState, ethereum_address: EthAddress) {
            assert(!ethereum_address.is_zero(), 'AR_ZERO_ADDRESS');
            let current = self.ethereum_to_starknet.read(ethereum_address);
            assert(!current.is_zero(), 'AR_NOT_LINKED');
            assert(get_caller_address() == current, 'AR_BAD_CALLER');
            let nonce = state::next_nonce(self.ethereum_nonce.read(ethereum_address));
            let recipient = state::next_nonce(
                self.recipient_nonce.read((current, ethereum_address)),
            );
            self.remove(ethereum_address, current);
            self
                .emit(
                    AssociationChanged {
                        ethereum_address,
                        previous_starknet_address: current,
                        new_starknet_address: 0.try_into().unwrap(),
                        operation: 3,
                    },
                );
            self.advance_ethereum(ethereum_address, nonce);
            self.advance_recipient(ethereum_address, current, recipient);
        }
        fn revoke(ref self: ContractState, request: RevokeRequest, signature: Signature) {
            let ethereum = request.ethereum_address;
            self.check_signed(ethereum, request.ethereum_nonce, request.deadline);
            let current = self.ethereum_to_starknet.read(ethereum);
            assert(current == request.current_account_address, 'AR_BAD_CURRENT_ACCOUNT');
            let message = eip712::revoke_hash(
                @request,
                self.revoke_statement_hash.read(),
                get_tx_info().chain_id,
                get_contract_address(),
            );
            signature::verify(
                eip712::envelope(self.domain_separator.read(), message), signature, ethereum,
            );
            let nonce = state::next_nonce(request.ethereum_nonce);
            if current.is_zero() {
                self.advance_ethereum(ethereum, nonce);
            } else {
                let recipient = state::next_nonce(self.recipient_nonce.read((current, ethereum)));
                self.remove(ethereum, current);
                self
                    .emit(
                        AssociationChanged {
                            ethereum_address: ethereum,
                            previous_starknet_address: current,
                            new_starknet_address: 0.try_into().unwrap(),
                            operation: 4,
                        },
                    );
                self.advance_ethereum(ethereum, nonce);
                self.advance_recipient(ethereum, current, recipient);
            }
        }
        fn invalidate_pending_incoming(ref self: ContractState, ethereum_address: EthAddress) {
            let caller = get_caller_address();
            assert(!ethereum_address.is_zero() && !caller.is_zero(), 'AR_ZERO_ADDRESS');
            let recipient = state::next_nonce(
                self.recipient_nonce.read((caller, ethereum_address)),
            );
            self.advance_recipient(ethereum_address, caller, recipient);
        }
        fn get_starknet_address(
            self: @ContractState, ethereum_address: EthAddress,
        ) -> ContractAddress {
            self.ethereum_to_starknet.read(ethereum_address)
        }
        fn is_associated(
            self: @ContractState, ethereum_address: EthAddress, starknet_address: ContractAddress,
        ) -> bool {
            !ethereum_address.is_zero()
                && !starknet_address.is_zero()
                && self.ethereum_to_starknet.read(ethereum_address) == starknet_address
        }
        fn get_ethereum_address_count(
            self: @ContractState, starknet_address: ContractAddress,
        ) -> u64 {
            self.ethereum_count.read(starknet_address)
        }
        fn get_ethereum_addresses(
            self: @ContractState, starknet_address: ContractAddress, offset: u64, limit: u32,
        ) -> Array<EthAddress> {
            let length = state::page_length(
                self.ethereum_count.read(starknet_address), offset, limit,
            );
            let mut result = array![];
            for index in 0..length {
                result.append(self.ethereum_addresses.read((starknet_address, offset + index)));
            }
            result
        }
        fn get_ethereum_nonce(self: @ContractState, ethereum_address: EthAddress) -> u256 {
            self.ethereum_nonce.read(ethereum_address)
        }
        fn get_recipient_nonce(
            self: @ContractState, starknet_address: ContractAddress, ethereum_address: EthAddress,
        ) -> u256 {
            self.recipient_nonce.read((starknet_address, ethereum_address))
        }
        fn get_signing_domain(self: @ContractState) -> SigningDomain {
            let account_label = self.account_label.read();
            let (link_statement, move_statement, revoke_statement) = labels::statements(
                @account_label,
            );
            let chain = get_tx_info().chain_id;
            SigningDomain {
                name: "Account Address Association",
                version: "1",
                ethereum_chain_id: self.ethereum_chain_id.read(),
                account_chain_id: chain,
                registry_address: get_contract_address(),
                salt: self.domain_salt.read(),
                domain_separator: self.domain_separator.read(),
                account_label,
                link_statement,
                move_statement,
                revoke_statement,
                account_network_name: if chain == 'SN_MAIN' {
                    "Starknet Mainnet"
                } else {
                    "Starknet Sepolia"
                },
            }
        }
        fn get_version(self: @ContractState) -> felt252 {
            '1'
        }
    }
}
