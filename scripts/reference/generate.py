#!/usr/bin/env python3
"""Independent test oracle: maintained EIP-712 encoder, native recovery, PyCryptodome Keccak.

No production SDK/Cairo hashing or serialization implementation is imported.
All signing keys and addresses below are synthetic public test fixtures, never deployments.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import sys

from Crypto.Hash import keccak
from eth_account.messages import encode_typed_data
from eth_keys import KeyAPI
from eth_keys.backends import NativeECCBackend

ROOT = Path(__file__).resolve().parents[2]
APPROVED = "5beae0d4f74dfc4ed9cc664db98d28e5c4f5b96a"
DOMAIN = "EIP712Domain(string name,string version,uint256 chainId,bytes32 salt)"
DOMAIN_NAME = "Account Address Association"
DOMAIN_VERSION = "1"
SALT_NAMESPACE = "Account Address Association/v1"
TYPE_STRINGS = {
    "LinkAddress": "LinkAddress(string statement,address ethereumAddress,bytes32 accountAddress,uint256 accountChainId,bytes32 registryAddress,uint256 ethereumNonce,uint256 recipientNonce,uint64 deadline)",
    "MoveAddress": "MoveAddress(string statement,address ethereumAddress,bytes32 accountAddress,bytes32 previousAccountAddress,uint256 accountChainId,bytes32 registryAddress,uint256 ethereumNonce,uint256 recipientNonce,uint64 deadline)",
    "RevokeAssociation": "RevokeAssociation(string statement,address ethereumAddress,bytes32 currentAccountAddress,uint256 accountChainId,bytes32 registryAddress,uint256 ethereumNonce,uint64 deadline)",
}
TEMPLATES = {
    "LinkAddress": "Link my Ethereum address to this {accountLabel} account. This does not approve asset transfers.",
    "MoveAddress": "Move my Ethereum address link from the previous {accountLabel} account shown here to this account. This does not approve asset transfers.",
    "RevokeAssociation": "Remove my Ethereum address link to the {accountLabel} account shown here, if any, and cancel requests using the current Ethereum nonce.",
}
CURVE_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
KEYS = KeyAPI(NativeECCBackend())


def check_schema_document(contents):
    """Tie the independent generator to the reviewed human-readable protocol."""
    lines = [DOMAIN, f"name: {DOMAIN_NAME}", f"version: {DOMAIN_VERSION}",
             f"salt_namespace: {SALT_NAMESPACE}", *TYPE_STRINGS.values(), *TEMPLATES.values()]
    if f"`{APPROVED}`" not in contents or any(
            len(re.findall(rf"(?m)^{re.escape(line)}$", contents)) != 1 for line in lines):
        raise ValueError("Reference type/statement differs from protocol/spec.md")


def k(data):
    return keccak.new(digest_bits=256, data=data).digest()


def hx(data):
    return "0x" + data.hex()


def word(value):
    return value.to_bytes(32, "big")


def fields(type_string):
    return [{"name": name, "type": kind} for kind, name in
            (part.split(" ") for part in type_string.split("(")[1][:-1].split(","))]


def limbs(value):
    return [str(value & ((1 << 128) - 1)), str(value >> 128)]


def byte_array_felts(text):
    data = text.encode("ascii")
    words = [data[index:index + 31] for index in range(0, len(data) - len(data) % 31, 31)]
    tail = data[len(words) * 31:]
    return [str(len(words)), *(str(int.from_bytes(item, "big")) for item in words),
            str(int.from_bytes(tail, "big")), str(len(tail))]


def selector(name):
    return str(int.from_bytes(k(name.encode()), "big") & ((1 << 250) - 1))


def struct_hash(type_string, message):
    result = k(type_string.encode())
    for item in fields(type_string):
        value = message[item["name"]]
        kind = item["type"]
        result += (k(value.encode()) if kind == "string" else bytes.fromhex(value[2:])
                   if kind == "bytes32" else word(int(value, 16)) if kind == "address" else word(int(value)))
    return k(result)


def fixture(chain, scenario, label, large=False):
    assert re.fullmatch(r"[A-Za-z0-9]+(?: [A-Za-z0-9]+)*", label) and 1 <= len(label) <= 48
    eth_chain, account_name, technical_name = chain
    account_chain = int.from_bytes(account_name.encode(), "big")
    registry = (1 << 249) + 0x123456789ABCDEF
    destination = (1 << 248) + 0x112233445566778899
    previous = 0 if scenario in {"link", "revoke_unlinked"} else (1 << 247) + 0xAABBCCDDEEFF
    nonce = (1 << 200) + 17 if large else 0
    recipient = (1 << 192) + 19 if large else 0
    old_recipient = (1 << 180) + 23 if large else 0
    deadline = (1 << 64) - 1 if large else 2_000_000_000
    # Public scalar 1 is an intentionally unsafe test key; never fund any fixture address.
    private = KEYS.PrivateKey(word(1), backend=KEYS.backend)
    ethereum = private.public_key.to_checksum_address()
    primary = {"link": "LinkAddress", "move": "MoveAddress", "revoke_linked": "RevokeAssociation",
               "revoke_unlinked": "RevokeAssociation"}[scenario]
    statement = TEMPLATES[primary].format(accountLabel=label)
    salt_preimage = k(SALT_NAMESPACE.encode()) + word(account_chain) + word(registry)
    domain = {"name": DOMAIN_NAME, "version": DOMAIN_VERSION, "chainId": str(eth_chain), "salt": hx(k(salt_preimage))}
    message = {"statement": statement, "ethereumAddress": ethereum}
    if scenario in {"link", "move"}:
        message["accountAddress"] = hx(word(destination))
    if scenario == "move":
        message["previousAccountAddress"] = hx(word(previous))
    if scenario.startswith("revoke"):
        message["currentAccountAddress"] = hx(word(previous))
    message.update(accountChainId=str(account_chain), registryAddress=hx(word(registry)), ethereumNonce=str(nonce))
    if scenario in {"link", "move"}:
        message["recipientNonce"] = str(recipient)
    message["deadline"] = str(deadline)
    typed = {"types": {"EIP712Domain": fields(DOMAIN), primary: fields(TYPE_STRINGS[primary])},
             "primaryType": primary, "domain": domain, "message": message}
    encoded = encode_typed_data(full_message=typed)
    assert encoded.header == struct_hash(DOMAIN, domain)
    assert encoded.body == struct_hash(TYPE_STRINGS[primary], message)
    digest = k(b"\x19" + encoded.version + encoded.header + encoded.body)
    signature = KEYS.ecdsa_sign(digest, private)
    assert 1 <= signature.r < CURVE_N and 1 <= signature.s <= CURVE_N // 2
    recovered = KEYS.ecdsa_recover(digest, signature).to_checksum_address()
    assert recovered == ethereum
    signature_calldata = limbs(signature.r) + limbs(signature.s) + [str(signature.v)]
    request = [str(int(ethereum, 16)), str(destination if scenario in {"link", "move"} else previous)]
    if scenario == "move":
        request += [str(previous)]
    request += limbs(nonce)
    if scenario in {"link", "move"}:
        request += limbs(recipient)
    request += [str(deadline)]
    new_account = destination if scenario in {"link", "move"} else 0
    events = []
    if previous != new_account:
        events.append({"name": "AssociationChanged", "keys": [selector("AssociationChanged"), str(int(ethereum, 16))],
                       "data": [str(previous), str(new_account), str({"link": 1, "move": 2, "revoke_linked": 4}[scenario])]})
    events.append({"name": "EthereumNonceAdvanced", "keys": [selector("EthereumNonceAdvanced"), str(int(ethereum, 16))], "data": limbs(nonce + 1)})
    recipient_after = []
    for account, value in ([(previous, old_recipient)] if previous else []) + ([(destination, recipient)] if new_account else []):
        recipient_after.append({"account": str(account), "before": str(value), "after": str(value + 1)})
        events.append({"name": "RecipientNonceAdvanced", "keys": [selector("RecipientNonceAdvanced"), str(account), str(int(ethereum, 16))], "data": limbs(value + 1)})
    conventional = word(signature.r) + word(signature.s)
    compact = word(signature.r) + word(signature.s | (signature.v << 255))
    return {"id": f"{account_name.lower()}-{scenario}-label{len(label)}-{'large' if large else 'zero'}",
            "fixture_only": True, "test_key_scalar": "1 (PUBLIC TEST ONLY; NEVER FUND)", "account_label": label,
            "account_network_name": technical_name, "typed_data": typed,
            "hashes": {"salt_preimage": hx(salt_preimage), "salt": domain["salt"], "type_hash": hx(k(TYPE_STRINGS[primary].encode())),
                       "statement_hash": hx(k(statement.encode())), "domain_separator": hx(encoded.header), "struct_hash": hx(encoded.body), "digest": hx(digest)},
            "signature": {"r": str(signature.r), "s": str(signature.s), "y_parity": signature.v,
                          "v_0_1": hx(conventional + bytes([signature.v])), "v_27_28": hx(conventional + bytes([signature.v + 27])),
                          "erc2098": hx(compact), "recovered_address": recovered},
            "calldata": {"entrypoint": scenario.split("_")[0], "selector": selector(scenario.split("_")[0]), "request": request,
                         "signature": signature_calldata, "full": request + signature_calldata},
            "bytearray": {"account_label": byte_array_felts(label), "statement": byte_array_felts(statement)},
            "expected": {"mapping_before": str(previous), "mapping_after": str(new_account), "ethereum_nonce_before": str(nonce),
                         "ethereum_nonce_after": str(nonce + 1), "recipient_nonces": recipient_after, "events": events}}


def deployment(chain, label):
    eth_chain, account_name, technical_name = chain
    account_chain = int.from_bytes(account_name.encode(), "big")
    registry = (1 << 249) + 0x123456789ABCDEF
    salt = k(k(SALT_NAMESPACE.encode()) + word(account_chain) + word(registry))
    domain = {"name": DOMAIN_NAME, "version": DOMAIN_VERSION, "chainId": str(eth_chain), "salt": hx(salt)}
    separator = struct_hash(DOMAIN, domain)
    text = {name: template.format(accountLabel=label) for name, template in TEMPLATES.items()}
    discovery = (byte_array_felts(domain["name"]) + byte_array_felts(DOMAIN_VERSION) + limbs(eth_chain) + [str(account_chain), str(registry)]
                 + limbs(int.from_bytes(salt, "big")) + limbs(int.from_bytes(separator, "big")) + byte_array_felts(label)
                 + byte_array_felts(text["LinkAddress"]) + byte_array_felts(text["MoveAddress"])
                 + byte_array_felts(text["RevokeAssociation"]) + byte_array_felts(technical_name))
    logical = {"name": domain["name"], "version": DOMAIN_VERSION, "ethereum_chain_id": eth_chain, "account_chain_id": account_chain,
               "registry_address": registry, "salt": int.from_bytes(salt, "big"), "domain_separator": int.from_bytes(separator, "big"),
               "account_label": label, "link_statement": text["LinkAddress"], "move_statement": text["MoveAddress"],
               "revoke_statement": text["RevokeAssociation"], "account_network_name": technical_name}
    abi = json.loads((ROOT / "protocol/abi.json").read_text())
    if serialize_abi(abi, "contracts::interface::SigningDomain", logical) != discovery:
        raise ValueError("Compiler discovery ABI differs from independent return serialization")
    constructor = next(entry for entry in abi if entry["type"] == "constructor")
    values = {"ethereum_chain_id": eth_chain, "account_label": label}
    actual = [felt for item in constructor["inputs"] for felt in serialize_abi(abi, item["type"], values[item["name"]])]
    if actual != limbs(eth_chain) + byte_array_felts(label):
        raise ValueError("Compiler constructor ABI differs from independent calldata")
    return {"fixture_only": True, "account_chain": account_name, "account_label": label,
            "constructor_calldata": limbs(eth_chain) + byte_array_felts(label),
            "get_signing_domain_return": discovery, "get_version_return": [str(ord("1"))]}


def unsigned_fixture(chain, operation):
    ethereum = int(KEYS.PrivateKey(word(1), backend=KEYS.backend).public_key.to_address(), 16)
    account = (1 << 248) + 0x112233445566778899
    nonce, recipient = (1 << 200) + 17, (1 << 192) + 19
    events = []
    if operation == "unlink":
        events += [{"name": "AssociationChanged", "keys": [selector("AssociationChanged"), str(ethereum)],
                    "data": [str(account), "0", "3"]},
                   {"name": "EthereumNonceAdvanced", "keys": [selector("EthereumNonceAdvanced"), str(ethereum)], "data": limbs(nonce + 1)}]
    events.append({"name": "RecipientNonceAdvanced", "keys": [selector("RecipientNonceAdvanced"), str(account), str(ethereum)], "data": limbs(recipient + 1)})
    return {"fixture_only": True, "id": chain[1].lower() + "-" + operation,
            "entrypoint": operation, "selector": selector(operation), "caller": str(account), "calldata": [str(ethereum)],
            "expected": {"mapping_before": str(account), "mapping_after": "0" if operation == "unlink" else str(account),
                         "ethereum_nonce_before": str(nonce), "ethereum_nonce_after": str(nonce + (operation == "unlink")),
                         "recipient_nonce_before": str(recipient), "recipient_nonce_after": str(recipient + 1), "events": events}}


def serialize_abi(abi, type_name, value):
    if type_name == "core::byte_array::ByteArray":
        return byte_array_felts(value)
    if type_name == "core::integer::u256":
        return limbs(value)
    if type_name in {"core::felt252", "core::integer::u8", "core::integer::u32", "core::integer::u64",
                     "core::starknet::eth_address::EthAddress", "core::starknet::contract_address::ContractAddress", "core::bool"}:
        return [str(int(value))]
    entries = [entry for entry in abi if entry.get("name") == type_name and entry["type"] == "struct"]
    if len(entries) != 1 or set(value) != {member["name"] for member in entries[0]["members"]}:
        raise ValueError(f"Reference values differ from compiler ABI struct: {type_name}")
    return [felt for member in entries[0]["members"] for felt in serialize_abi(abi, member["type"], value[member["name"]])]


def check_abi_agreement(abi, vectors):
    interface = next(entry for entry in abi if entry.get("name") == "contracts::interface::IAddressRegistry")
    expected_methods = {"link", "move", "unlink", "revoke", "invalidate_pending_incoming", "get_starknet_address", "is_associated",
                        "get_ethereum_address_count", "get_ethereum_addresses", "get_ethereum_nonce", "get_recipient_nonce", "get_signing_domain", "get_version"}
    if {method["name"] for method in interface["items"]} != expected_methods:
        raise ValueError("Public method inventory differs from the approved agreement")
    prefix = "contracts::registry::EthereumAddressAssociationRegistry::"
    layouts = {
        "AssociationChanged": [("ethereum_address", "core::starknet::eth_address::EthAddress", "key"),
                               ("previous_starknet_address", "core::starknet::contract_address::ContractAddress", "data"),
                               ("new_starknet_address", "core::starknet::contract_address::ContractAddress", "data"), ("operation", "core::integer::u8", "data")],
        "EthereumNonceAdvanced": [("ethereum_address", "core::starknet::eth_address::EthAddress", "key"), ("new_nonce", "core::integer::u256", "data")],
        "RecipientNonceAdvanced": [("starknet_address", "core::starknet::contract_address::ContractAddress", "key"),
                                   ("ethereum_address", "core::starknet::eth_address::EthAddress", "key"), ("new_nonce", "core::integer::u256", "data")],
    }
    for name, expected in layouts.items():
        event = next(entry for entry in abi if entry.get("name") == prefix + name)
        if [(item["name"], item["type"], item["kind"]) for item in event["members"]] != expected:
            raise ValueError("Compiler event key/data layout differs from independent fixtures")
    root_event = next(entry for entry in abi if entry.get("name") == prefix + "Event")
    if root_event["variants"] != [{"name": name, "type": prefix + name, "kind": "nested"} for name in layouts]:
        raise ValueError("Compiler Event namespace or variant nesting differs from freeze")
    for vector in vectors:
        message = vector["typed_data"]["message"]
        names = {"ethereumAddress": "ethereum_address", "accountAddress": "account_address", "previousAccountAddress": "previous_account_address",
                 "currentAccountAddress": "current_account_address", "ethereumNonce": "ethereum_nonce", "recipientNonce": "recipient_nonce", "deadline": "deadline"}
        request = {target: int(message[source], 16) if message[source].startswith("0x") else int(message[source])
                   for source, target in names.items() if source in message}
        signature = {"r": int(vector["signature"]["r"]), "s": int(vector["signature"]["s"]), "y_parity": vector["signature"]["y_parity"]}
        method = next(method for method in interface["items"] if method["name"] == vector["calldata"]["entrypoint"])
        if [item["name"] for item in method["inputs"]] != ["request", "signature"]:
            raise ValueError("Signed entrypoint input names/order drift")
        actual = serialize_abi(abi, method["inputs"][0]["type"], request) + serialize_abi(abi, method["inputs"][1]["type"], signature)
        if actual != vector["calldata"]["full"]:
            raise ValueError("Compiler ABI serialization differs from independent calldata")


def check_unsigned_agreement(abi, vectors):
    interface = next(entry for entry in abi if entry.get("name") == "contracts::interface::IAddressRegistry")
    expected_input = [{"name": "ethereum_address", "type": "core::starknet::eth_address::EthAddress"}]
    for vector in vectors:
        operation = vector["entrypoint"]
        if operation not in {"unlink", "invalidate_pending_incoming"}:
            raise ValueError("Unsigned entrypoint name differs from agreement")
        matches = [method for method in interface["items"] if method["name"] == operation]
        if len(matches) != 1 or matches[0]["inputs"] != expected_input:
            raise ValueError("Unsigned entrypoint input names/arity/types differ from agreement")
        ethereum = int(KEYS.PrivateKey(word(1), backend=KEYS.backend).public_key.to_address(), 16)
        actual = serialize_abi(abi, matches[0]["inputs"][0]["type"], ethereum)
        if vector["calldata"] != actual:
            raise ValueError("Unsigned calldata differs from compiler ABI")


def generate():
    chains = [(1, "SN_MAIN", "Starknet Mainnet"), (11155111, "SN_SEPOLIA", "Starknet Sepolia")]
    vectors = [fixture(chain, scenario, "Loot Survivor", large=index == 1)
               for index, chain in enumerate(chains) for scenario in ["link", "move", "revoke_linked", "revoke_unlinked"]]
    vectors += [fixture(chains[index % 2], "link", "A" * size, large=True) for index, size in enumerate([1, 30, 31, 32, 48])]
    abi = json.loads((ROOT / "protocol/abi.json").read_text())
    check_abi_agreement(abi, vectors)
    selectors = {item["name"]: selector(item["name"]) for entry in abi for item in
                 (entry.get("items", []) if entry["type"] == "interface" else [entry]) if item["type"] in {"function", "constructor"}}
    unsigned = [unsigned_fixture(chain, operation) for chain in chains for operation in ["unlink", "invalidate_pending_incoming"]]
    check_unsigned_agreement(abi, unsigned)
    return {"schema_version": 1, "approved_signing_revision": APPROVED,
            "fixture_warning": "Synthetic fixtures only. No real deployment or funded wallet. Public scalar 1 must never hold assets.",
            "domain_type": DOMAIN, "type_strings": TYPE_STRINGS, "statement_templates": TEMPLATES,
            "type_hashes": {name: hx(k(value.encode())) for name, value in {"EIP712Domain": DOMAIN, **TYPE_STRINGS}.items()},
            "selectors": selectors,
            "deployments": [deployment(chain, "Loot Survivor") for chain in chains]
                           + [deployment(chains[index % 2], "A" * size) for index, size in enumerate([1, 30, 31, 32, 48])],
            "unsigned_vectors": unsigned,
            "vectors": vectors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    lock_path = ROOT / "scripts/reference/wheels.lock.json"
    lock = json.loads(lock_path.read_text())
    if sys.version_info[:3] != tuple(map(int, lock["python"].split("."))) or sys.prefix == sys.base_prefix:
        raise ValueError("Run with the pinned private reference venv")
    for name, package in {"pip": lock["pip"], **lock["packages"]}.items():
        if importlib.metadata.version(name) != package["version"]:
            raise ValueError(f"Reference package drift: {name}")
    check_schema_document((ROOT / "protocol/spec.md").read_text())
    result = generate()
    contents = (json.dumps(result, indent=2) + "\n").encode()
    provenance = {"schema_version": 1, "python": lock["python"], "packages": {name: value["version"] for name, value in lock["packages"].items()},
                  "pip": lock["pip"]["version"], "backend": "eth_keys.backends.NativeECCBackend (explicit)",
                  "keccak": "Crypto.Hash.keccak (PyCryptodome)", "encoder": "eth_account.messages.encode_typed_data",
                  "cross_check": "independent reference struct-word encoding equals maintained encoder domain and message hashes",
                  "lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
                  "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "vectors_sha256": hashlib.sha256(contents).hexdigest()}
    for name, value in {"vectors.json": contents, "vectors.provenance.json": (json.dumps(provenance, indent=2) + "\n").encode()}.items():
        path = ROOT / "protocol" / name
        if args.write:
            path.write_bytes(value)
        elif not path.is_file() or path.read_bytes() != value:
            raise ValueError(f"Independent reference artifact drift: {name}")
    print(f"Verified {len(result['vectors'])} independent fixtures with native recovery")


if __name__ == "__main__":
    main()
