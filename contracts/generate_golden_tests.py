"""Derive regression inputs from frozen independent vectors, never compute expected hashes."""
import json
from pathlib import Path
from generated_output import write_generated
root = Path(__file__).resolve().parents[1]
v = json.loads((root / 'protocol/vectors.json').read_text())
lines = ['// Generated inputs from frozen independent protocol/vectors.json; expected hashes are not recomputed.', 'use contracts::{eip712, labels, signature};', 'use contracts::interface::{LinkRequest, MoveRequest, RevokeRequest, Signature};']
for i, x in enumerate(v['vectors']):
    m = x['typed_data']['message']
    op = x['calldata']['entrypoint']
    typ = {'link': 'LinkRequest', 'move': 'MoveRequest', 'revoke': 'RevokeRequest'}[op]
    fields = {'ethereumAddress': 'ethereum_address', 'accountAddress': 'account_address', 'previousAccountAddress': 'previous_account_address', 'currentAccountAddress': 'current_account_address', 'ethereumNonce': 'ethereum_nonce', 'recipientNonce': 'recipient_nonce', 'deadline': 'deadline'}
    lines += ['#[test]', f'fn golden_{i}_{op}() {{', f'    let label: ByteArray = {json.dumps(x['account_label'])};', '    labels::validate(@label);', '    let (link, movement, revoke) = labels::statements(@label);', f'    let statement = {dict(link='link', move='movement', revoke='revoke')[op]};']
    lines += ['    let _ = ' + {'link': '(movement, revoke)', 'move': '(link, revoke)', 'revoke': '(link, movement)'}[op] + ';', f"    assert(statement == {json.dumps(m['statement'])}, 'STATEMENT');", f"    assert(eip712::hash_text(@statement) == {x['hashes']['statement_hash']}, 'STATEMENT_HASH');", f'    let request = {typ} {{']
    for a, b in fields.items():
        if a in m:
            lines += [f'        {b}: {m[a]}.try_into().unwrap(),' if 'Address' in a else f'        {b}: {m[a]},']
    lines += ['    };', f'    let registry = {m['registryAddress']}.try_into().unwrap();', f'    let salt = eip712::salt({m['accountChainId']}, registry);', f"    assert(salt == {x['hashes']['salt']}, 'SALT');", f'    let domain = eip712::domain({x['typed_data']['domain']['chainId']}, salt);', f"    assert(domain == {x['hashes']['domain_separator']}, 'DOMAIN');", f'    let message = eip712::{op}_hash(@request, eip712::hash_text(@statement), {m['accountChainId']}, registry);', f"    assert(message == {x['hashes']['struct_hash']}, 'STRUCT');", '    let digest = eip712::envelope(domain, message);', f"    assert(digest == {x['hashes']['digest']}, 'DIGEST');", f'    let sig = Signature {{ r: {x['signature']['r']}, s: {x['signature']['s']}, y_parity: {str(bool(x['signature']['y_parity'])).lower()} }};', '    let mut calldata = array![];', '    Serde::serialize(@request, ref calldata);', '    Serde::serialize(@sig, ref calldata);', f"    assert(calldata == array![{', '.join(x['calldata']['full'])}], 'CALLDATA');", '    signature::verify(digest, sig, request.ethereum_address);', '}']
write_generated(root / 'contracts/tests/test_golden.cairo', '\n'.join(lines) + '\n')
