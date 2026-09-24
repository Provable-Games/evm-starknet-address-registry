use contracts::eip712;
use contracts::interface::{
    IAddressRegistryDispatcher, IAddressRegistryDispatcherTrait, IAddressRegistrySafeDispatcher,
    IAddressRegistrySafeDispatcherTrait,
};
use snforge_std::start_cheat_caller_address;
use starknet::SyscallResultTrait;
use starknet::secp256_trait::Secp256Trait;
use starknet::secp256k1::Secp256k1Point;
use crate::helpers::{deploy, eth, link_request, sign};
#[test]
#[feature("safe_dispatcher")]
fn domain_fields_and_signature_ranges() {
    let registry = deploy('SN_MAIN', 1, "A");
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let safe = IAddressRegistrySafeDispatcher { contract_address: registry };
    let a = 111.try_into().unwrap();
    start_cheat_caller_address(registry, a);
    for case in 0..13_u32 {
        let (request, mut signature) = link_request(registry, 1, a);
        let domain = reader.get_signing_domain();
        let digest = match case {
            0 => {
                eip712::envelope(
                    eip712::domain(11155111, domain.salt),
                    eip712::link_hash(
                        @request,
                        eip712::hash_text(@domain.link_statement),
                        domain.account_chain_id,
                        registry,
                    ),
                )
            },
            1 => {
                eip712::envelope(
                    domain.domain_separator,
                    eip712::link_hash(
                        @request, eip712::hash_text(@domain.link_statement), 'SN_SEPOLIA', registry,
                    ),
                )
            },
            2 => {
                eip712::envelope(
                    domain.domain_separator,
                    eip712::link_hash(
                        @request,
                        eip712::hash_text(@domain.link_statement),
                        domain.account_chain_id,
                        333.try_into().unwrap(),
                    ),
                )
            },
            3 => {
                eip712::envelope(
                    domain.domain_separator,
                    eip712::link_hash(
                        @request,
                        eip712::hash_text(
                            @"Link my Ethereum address to this B account. This does not approve asset transfers.",
                        ),
                        domain.account_chain_id,
                        registry,
                    ),
                )
            },
            4 => {
                eip712::envelope(
                    domain.domain_separator,
                    eip712::link_hash(
                        @request,
                        eip712::hash_text(@domain.move_statement),
                        domain.account_chain_id,
                        registry,
                    ),
                )
            },
            12 => {
                eip712::envelope(
                    domain.domain_separator,
                    eip712::hash_words(
                        array![
                            eip712::hash_text(@"WrongType"),
                            eip712::hash_text(@domain.link_statement),
                            eip712::ethereum_word(request.ethereum_address),
                            eip712::account_word(request.account_address),
                            domain.account_chain_id.into(), eip712::account_word(registry),
                            request.ethereum_nonce, request.recipient_nonce,
                            request.deadline.into(),
                        ]
                            .span(),
                    ),
                )
            },
            _ => { 1 },
        };
        if case < 5 || case == 12 {
            signature = sign(1, digest);
        } else if case == 5 {
            signature.r = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141;
        } else if case == 6 {
            signature.r = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364142;
        } else if case == 7 {
            signature.s = 0x7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a1;
        } else if case == 8 {
            signature.s = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141;
        } else if case == 9 {
            signature.r = 0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff;
        } else if case == 10 {
            signature.r = 5;
            signature.s = 1;
        } else {
            signature.r = u256 { low: signature.r.high, high: signature.r.low };
        }
        assert(
            *safe.link(request, signature).unwrap_err().at(0) == 'AR_BAD_SIGNATURE',
            'CRYPTO_REJECT',
        );
        assert(reader.get_ethereum_nonce(eth(1)) == 0, 'NO_CRYPTO_WRITES');
    };
}
#[test]
fn native_abi_rejects_bad_width_limb_and_parity() {
    let registry = deploy('SN_MAIN', 1, "A");
    start_cheat_caller_address(registry, 111.try_into().unwrap());
    for case in 0..7_u32 {
        let (request, signature) = link_request(registry, 1, 111.try_into().unwrap());
        let mut canonical = array![];
        Serde::serialize(@request, ref canonical);
        Serde::serialize(@signature, ref canonical);
        let mut malformed = array![];
        let length = if case == 4 {
            canonical.len() - 1
        } else {
            canonical.len()
        };
        for index in 0..length {
            let value = if case == 0 && index == 0 {
                0x10000000000000000000000000000000000000000
            } else if case == 1 && index == 1 {
                0x800000000000000000000000000000000000000000000000000000000000000
            } else if case == 2 && index == 2 {
                0x100000000000000000000000000000000
            } else if (case == 3 || case == 6) && index == 11 {
                if case == 3 {
                    2
                } else {
                    0x800000000000011000000000000000000000000000000000000000000000000
                }
            } else {
                *canonical.at(index)
            };
            malformed.append(value);
        }
        if case == 5 {
            malformed.append(0);
        }
        assert!(
            starknet::syscalls::call_contract_syscall(registry, selector!("link"), malformed.span())
                .is_err(),
            "ABI range rejection case={}",
            case,
        );
    };
}

#[test]
#[feature("safe_dispatcher")]
fn noncurve_recovery_returns_stable_signature_error() {
    let registry = deploy('SN_MAIN', 1, "A");
    let reader = IAddressRegistryDispatcher { contract_address: registry };
    let safe = IAddressRegistrySafeDispatcher { contract_address: registry };
    let a = 111.try_into().unwrap();
    start_cheat_caller_address(registry, a);
    for y_parity in array![false, true] {
        // x=5 has no secp256k1 point. The pinned core recovery must propagate
        // this None into its Result error, allowing our stable application error.
        assert!(
            Secp256Trait::<Secp256k1Point>::secp256_ec_get_point_from_x_syscall(5, y_parity)
                .unwrap_syscall()
                .is_none(),
            "noncurve fixture",
        );
        let (request, mut signature) = link_request(registry, 1, a);
        signature.r = 5;
        signature.s = 1;
        signature.y_parity = y_parity;
        let error = safe.link(request, signature).unwrap_err();
        assert!(*error.at(0) == 'AR_BAD_SIGNATURE', "recovery error: {:?}", error);
        assert!(reader.get_ethereum_nonce(eth(1)) == 0);
        assert!(reader.get_ethereum_address_count(a) == 0);
        assert!(reader.get_starknet_address(eth(1)) == 0.try_into().unwrap());
    };
}
