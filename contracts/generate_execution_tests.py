"""Freeze test inputs directly from independent vectors, with explicit test-only state seeding."""
import json
from pathlib import Path
from generated_output import write_generated
root = Path(__file__).resolve().parents[1]
v = json.loads((root / 'protocol/vectors.json').read_text())
lines = ['// Generated from independent protocol/vectors.json; storage seeding is test-only.', 'use contracts::interface::{IAddressRegistryDispatcher, IAddressRegistryDispatcherTrait};', 'use snforge_std::{declare, ContractClassTrait, DeclareResultTrait, start_cheat_chain_id_global, start_cheat_block_timestamp_global, start_cheat_caller_address, spy_events, EventSpyTrait};', 'use snforge_std::cheatcodes::storage::{store, map_entry_address};', 'use snforge_std::cheatcodes::events::Event;', 'use starknet::{ContractAddress, SyscallResultTrait};']

def arr(values):
    return 'array![' + ', '.join(map(str, values)) + ']'

def store(name, keys, vals):
    return f'    store(registry, map_entry_address(selector!("{name}"), {arr(keys)}.span()), {arr(vals)}.span());'

def limbs(n):
    n = int(n)
    return [n % 2 ** 128, n // 2 ** 128]
for i, x in enumerate(v['vectors']):
    m = x['typed_data']['message']
    e = x['expected']
    eth = int(m['ethereumAddress'], 16)
    previous = int(e['mapping_before'])
    chain = m['accountChainId']
    ethchain = x['typed_data']['domain']['chainId']
    reg = int(m['registryAddress'], 16)
    lines += ['#[test]', f'fn execute_golden_{i}() {{', f'    start_cheat_chain_id_global({chain});', '    start_cheat_block_timestamp_global(100);', f'    let registry: ContractAddress = {reg}.try_into().unwrap();', '    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();', f'    class.deploy_at(@{arr(limbs(ethchain) + x['bytearray']['account_label'])}, registry).unwrap_syscall();', store('ethereum_nonce', [eth], limbs(e['ethereum_nonce_before']))]
    if previous:
        lines += [store('ethereum_to_starknet', [eth], [previous]), store('ethereum_count', [previous], [1]), store('ethereum_addresses', [previous, 0], [eth]), store('ethereum_index_plus_one', [eth], [1])]
    for p in e['recipient_nonces']:
        lines += [store('recipient_nonce', [p['account'], eth], limbs(p['before']))]
    caller = int(m.get('accountAddress', '0x999'), 16)
    lines += [f'    start_cheat_caller_address(registry, {caller}.try_into().unwrap());', '    let mut spy = spy_events();', f'    starknet::syscalls::call_contract_syscall(registry, {x['calldata']['selector']}, {arr(x['calldata']['full'])}.span()).unwrap_syscall();', '    let reader = IAddressRegistryDispatcher { contract_address: registry };', f'    let ethereum = {eth}.try_into().unwrap();', f"    assert(reader.get_starknet_address(ethereum) == {e['mapping_after']}.try_into().unwrap(), 'GOLD_MAPPING');", f"    assert(reader.get_ethereum_nonce(ethereum) == {e['ethereum_nonce_after']}, 'GOLD_NONCE');"]
    for p in e['recipient_nonces']:
        lines += [f"    assert(reader.get_recipient_nonce({p['account']}.try_into().unwrap(), ethereum) == {p['after']}, 'GOLD_PAIR');"]
    events = ', '.join((f'(registry, Event {{ keys: {arr(event['keys'])}, data: {arr(event['data'])} }})' for event in e['events']))
    lines += [f"    assert(spy.get_events().events == array![{events}], 'GOLD_EVENTS');", '}']
for i, x in enumerate(v['unsigned_vectors']):
    e = x['expected']
    ethereum = int(x['calldata'][0])
    account = int(x['caller'])
    chain = 'SN_MAIN' if x['id'].startswith('sn_main') else 'SN_SEPOLIA'
    ethchain = 1 if chain == 'SN_MAIN' else 11155111
    reg = (1 << 249) + 81985529216486895
    lines += ['#[test]', f'fn unsigned_golden_{i}() {{', f"    start_cheat_chain_id_global('{chain}');", f'    let registry: ContractAddress = {reg}.try_into().unwrap();', '    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();', f'    class.deploy_at(@array![{ethchain}, 0, 0, 65, 1], registry).unwrap_syscall();', store('ethereum_to_starknet', [ethereum], [account]), store('ethereum_count', [account], [1]), store('ethereum_addresses', [account, 0], [ethereum]), store('ethereum_index_plus_one', [ethereum], [1]), store('ethereum_nonce', [ethereum], limbs(e['ethereum_nonce_before'])), store('recipient_nonce', [account, ethereum], limbs(e['recipient_nonce_before'])), f'    start_cheat_caller_address(registry, {account}.try_into().unwrap());', '    let mut spy = spy_events();', f'    starknet::syscalls::call_contract_syscall(registry, {x['selector']}, {arr(x['calldata'])}.span()).unwrap_syscall();', '    let reader = IAddressRegistryDispatcher { contract_address: registry };', f'    let ethereum = {ethereum}.try_into().unwrap();', f"    assert(reader.get_starknet_address(ethereum) == {e['mapping_after']}.try_into().unwrap(), 'UNSIGNED_MAPPING');", f"    assert(reader.get_ethereum_nonce(ethereum) == {e['ethereum_nonce_after']}, 'UNSIGNED_NONCE');", f"    assert(reader.get_recipient_nonce({account}.try_into().unwrap(), ethereum) == {e['recipient_nonce_after']}, 'UNSIGNED_PAIR');"]
    events = ', '.join((f'(registry, Event {{ keys: {arr(event['keys'])}, data: {arr(event['data'])} }})' for event in e['events']))
    lines += [f"    assert(spy.get_events().events == array![{events}], 'UNSIGNED_EVENTS');", '}']
for i, x in enumerate(v['deployments']):
    reg = (1 << 249) + 81985529216486895
    lines += ['#[test]', f'fn discovery_golden_{i}() {{', f"    start_cheat_chain_id_global('{x['account_chain']}');", f'    let registry: ContractAddress = {reg}.try_into().unwrap();', '    let class = declare("EthereumAddressAssociationRegistry").unwrap_syscall().contract_class();', f'    class.deploy_at(@{arr(x['constructor_calldata'])}, registry).unwrap_syscall();', '    let domain = IAddressRegistryDispatcher { contract_address: registry }.get_signing_domain();', '    let mut encoded = array![];', '    Serde::serialize(@domain, ref encoded);', f"    assert(encoded == {arr(x['get_signing_domain_return'])}, 'DISCOVERY_WORDS');", '}']
write_generated(root / 'contracts/tests/test_golden_execution.cairo', '\n'.join(lines) + '\n')
