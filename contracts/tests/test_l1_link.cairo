use contracts::interface::{
    IAddressRegistryDispatcher, IAddressRegistryDispatcherTrait, IL1LinkRegistryDispatcher,
    IL1LinkRegistryDispatcherTrait, IL1LinkRegistrySafeDispatcher,
    IL1LinkRegistrySafeDispatcherTrait, L1LinkProposal,
};
use snforge_std::{L1HandlerTrait, start_cheat_block_timestamp, start_cheat_caller_address};
use starknet::{ContractAddress, EthAddress, SyscallResult, SyscallResultTrait};
use crate::helpers::deploy;

fn deliver(
    registry: ContractAddress, sender: felt252, recipient: felt252, proposal: L1LinkProposal,
) -> SyscallResult<()> {
    let mut data = array![1, 11155111, 0, 'SN_SEPOLIA', registry.into(), recipient];
    proposal.serialize(ref data);
    L1HandlerTrait::new(registry, selector!("propose_link_from_l1")).execute(sender, data.span())
}

#[test]
#[feature("safe_dispatcher")]
fn l1_proposal_requires_destination_and_authenticated_origin() {
    let registry = deploy('SN_SEPOLIA', 11155111, "A");
    let links = IAddressRegistryDispatcher { contract_address: registry };
    let l1 = IL1LinkRegistryDispatcher { contract_address: registry };
    let safe = IL1LinkRegistrySafeDispatcher { contract_address: registry };
    let account: ContractAddress = 123.try_into().unwrap();
    let ethereum: EthAddress = 456.try_into().unwrap();
    let proposal = L1LinkProposal { ethereum_nonce: 0, recipient_nonce: 0, deadline: 100 };
    start_cheat_caller_address(registry, account);
    deliver(registry, 999, account.into(), proposal).unwrap_syscall();
    assert(
        *safe.accept_l1_link(ethereum, proposal).unwrap_err().at(0) == 'AR_NO_L1_PROPOSAL',
        'ORIGIN',
    );
    deliver(registry, ethereum.into(), account.into(), proposal).unwrap_syscall();
    assert(l1.get_l1_link_proposal(ethereum, account) == proposal, 'DELIVERED');
    assert(!links.is_associated(ethereum, account), 'PRE_CONSENT');
    assert(links.get_ethereum_address_count(account) == 0, 'NO_REVERSE');
    start_cheat_caller_address(registry, 321.try_into().unwrap());
    assert(
        *safe.accept_l1_link(ethereum, proposal).unwrap_err().at(0) == 'AR_NO_L1_PROPOSAL',
        'WRONG_RECIPIENT',
    );
    start_cheat_caller_address(registry, account);
    let changed = L1LinkProposal { deadline: 101, ..proposal };
    assert(
        *safe.accept_l1_link(ethereum, changed).unwrap_err().at(0) == 'AR_L1_PROPOSAL_CHANGED',
        'TAMPERED',
    );
    l1.accept_l1_link(ethereum, proposal);
    assert(links.is_associated(ethereum, account), 'LINKED');
    assert(links.get_ethereum_address_count(account) == 1, 'REVERSE');
    assert(links.get_ethereum_nonce(ethereum) == 1, 'ETH_NONCE');
    assert(links.get_recipient_nonce(account, ethereum) == 1, 'PAIR_NONCE');
    assert(l1.get_l1_link_proposal(ethereum, account).deadline == 0, 'CONSUMED');
    assert(
        *safe.accept_l1_link(ethereum, proposal).unwrap_err().at(0) == 'AR_NO_L1_PROPOSAL',
        'REPLAY',
    );
    let next = L1LinkProposal { ethereum_nonce: 1, recipient_nonce: 1, deadline: 100 };
    assert(deliver(registry, ethereum.into(), account.into(), next).is_err(), 'FIRST_LINK_ONLY');
    links.unlink(ethereum);
    assert(
        deliver(registry, ethereum.into(), account.into(), proposal).is_err(),
        'REPLAY_AFTER_UNLINK',
    );
}

#[test]
#[feature("safe_dispatcher")]
fn stored_l1_proposal_for_another_destination_stays_stale_after_unlink() {
    let registry = deploy('SN_SEPOLIA', 11155111, "A");
    let links = IAddressRegistryDispatcher { contract_address: registry };
    let l1 = IL1LinkRegistryDispatcher { contract_address: registry };
    let safe = IL1LinkRegistrySafeDispatcher { contract_address: registry };
    let first: ContractAddress = 123.try_into().unwrap();
    let second: ContractAddress = 321.try_into().unwrap();
    let ethereum: EthAddress = 456.try_into().unwrap();
    let proposal = L1LinkProposal { ethereum_nonce: 0, recipient_nonce: 0, deadline: 100 };
    deliver(registry, ethereum.into(), first.into(), proposal).unwrap_syscall();
    deliver(registry, ethereum.into(), second.into(), proposal).unwrap_syscall();
    start_cheat_caller_address(registry, first);
    l1.accept_l1_link(ethereum, proposal);
    links.unlink(ethereum);
    start_cheat_caller_address(registry, second);
    assert(l1.get_l1_link_proposal(ethereum, second) == proposal, 'STILL_STORED');
    assert(
        *safe.accept_l1_link(ethereum, proposal).unwrap_err().at(0) == 'AR_STALE_ETH_NONCE',
        'STALE_PROPOSAL',
    );
    assert(!links.is_associated(ethereum, second), 'NO_LINK');
}

#[test]
#[feature("safe_dispatcher")]
fn l1_cancel_in_flight_delivered_and_expired_proposals() {
    let registry = deploy('SN_SEPOLIA', 11155111, "A");
    let links = IAddressRegistryDispatcher { contract_address: registry };
    let safe = IL1LinkRegistrySafeDispatcher { contract_address: registry };
    let account: ContractAddress = 123.try_into().unwrap();
    let ethereum: EthAddress = 456.try_into().unwrap();
    let old = L1LinkProposal { ethereum_nonce: 0, recipient_nonce: 0, deadline: 105 };
    start_cheat_caller_address(registry, account);
    deliver(registry, ethereum.into(), account.into(), old).unwrap_syscall();
    links.invalidate_pending_incoming(ethereum);
    assert(
        *safe.accept_l1_link(ethereum, old).unwrap_err().at(0) == 'AR_STALE_RECIP_NONCE',
        'STORED_CANCEL',
    );
    assert(deliver(registry, ethereum.into(), account.into(), old).is_err(), 'IN_FLIGHT_CANCEL');
    let fresh = L1LinkProposal { recipient_nonce: 1, ..old };
    deliver(registry, ethereum.into(), account.into(), fresh).unwrap_syscall();
    assert(
        *safe.accept_l1_link(ethereum, old).unwrap_err().at(0) == 'AR_L1_PROPOSAL_CHANGED',
        'OLD_CONSENT',
    );
    start_cheat_block_timestamp(registry, 106);
    assert(
        *safe.accept_l1_link(ethereum, fresh).unwrap_err().at(0) == 'AR_EXPIRED', 'EXPIRED_CONSENT',
    );
    assert(deliver(registry, ethereum.into(), account.into(), fresh).is_err(), 'EXPIRED_DELIVERY');
    assert(!links.is_associated(ethereum, account), 'NO_LINK');
}

#[test]
fn l1_delivery_checks_version_domains_nonce_and_addresses() {
    let registry = deploy('SN_SEPOLIA', 11155111, "A");
    let handler = L1HandlerTrait::new(registry, selector!("propose_link_from_l1"));
    let canonical: Array<felt252> = array![
        1, 11155111, 0, 'SN_SEPOLIA', registry.into(), 123, 0, 0, 0, 0, 100,
    ];
    for position in 0..canonical.len() {
        let mut changed = array![];
        for i in 0..canonical.len() {
            let value = *canonical.at(i);
            changed
                .append(
                    if i == position {
                        if position == 5 || position == 10 {
                            0
                        } else {
                            value + 1
                        }
                    } else {
                        value
                    },
                );
        }
        assert(handler.clone().execute(456, changed.span()).is_err(), 'INVALID_PAYLOAD');
    }
    assert(handler.clone().execute(0, canonical.span()).is_err(), 'ZERO_SENDER');
    assert(
        handler
            .clone()
            .execute(0x10000000000000000000000000000000000000000, canonical.span())
            .is_err(),
        'WIDE_SENDER',
    );
    handler.execute(456, canonical.span()).unwrap_syscall();
}
