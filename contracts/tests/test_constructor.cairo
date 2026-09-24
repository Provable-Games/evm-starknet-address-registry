use snforge_std::{ContractClassTrait, DeclareResultTrait, declare, start_cheat_chain_id_global};
use starknet::SyscallResultTrait;
#[test]
fn invalid_constructor_configuration() {
    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();
    let mut non_ascii: ByteArray = "";
    non_ascii.append_byte(0xc3);
    non_ascii.append_byte(0xa9);
    for label in array![
        non_ascii, "", " A", "A ", "A  B", "A-B", "A\nB",
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    ]
        .span() {
        start_cheat_chain_id_global('SN_MAIN');
        let mut calldata = array![];
        Serde::serialize(@1_u256, ref calldata);
        Serde::serialize(label, ref calldata);
        let error = class.deploy(@calldata).unwrap_err();
        assert(*error.at(0) == 'AR_BAD_LABEL', 'LABEL_ERROR');
    }
    for pair in array![
        ('SN_MAIN', 11155111_u256), ('SN_SEPOLIA', 1_u256), ('LOCAL', 1_u256), ('SN_MAIN', 0_u256),
    ]
        .span() {
        let (chain, ethereum) = *pair;
        start_cheat_chain_id_global(chain);
        let mut calldata = array![];
        Serde::serialize(@ethereum, ref calldata);
        let label: ByteArray = "Valid";
        Serde::serialize(@label, ref calldata);
        let error = class.deploy(@calldata).unwrap_err();
        assert(*error.at(0) == 'AR_BAD_CHAIN_PAIR', 'CHAIN_ERROR');
    };
}
