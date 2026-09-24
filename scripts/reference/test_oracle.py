"""Behavior regressions for the independent oracle's cross-artifact checks."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("oracle", Path(__file__).with_name("generate.py"))
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


class OracleTests(unittest.TestCase):
    def setUp(self):
        self.abi = json.loads((oracle.ROOT / "protocol/abi.json").read_text())
        self.vector = oracle.fixture((1, "SN_MAIN", "Starknet Mainnet"), "move", "Loot Survivor", True)

    def test_maintained_encoding_recovery_and_compiler_calldata_agree(self):
        oracle.check_abi_agreement(self.abi, [self.vector])

    def test_normative_schema_document_catches_generator_drift(self):
        contents = (oracle.ROOT / "protocol/spec.md").read_text()
        oracle.check_schema_document(contents)
        for original in [oracle.DOMAIN, oracle.TYPE_STRINGS["MoveAddress"],
                         oracle.TEMPLATES["RevokeAssociation"], f"name: {oracle.DOMAIN_NAME}"]:
            with self.subTest(original=original), self.assertRaisesRegex(ValueError, "protocol/spec.md"):
                oracle.check_schema_document(contents.replace(original, original + " changed", 1))

    def test_reordered_request_members_fail_agreement(self):
        abi = copy.deepcopy(self.abi)
        request = next(item for item in abi if item.get("name") == "contracts::interface::MoveRequest")
        request["members"][1], request["members"][2] = request["members"][2], request["members"][1]
        with self.assertRaisesRegex(ValueError, "serialization differs"):
            oracle.check_abi_agreement(abi, [self.vector])

    def test_wrong_limb_order_fails_agreement(self):
        vector = copy.deepcopy(self.vector)
        vector["calldata"]["full"][3:5] = reversed(vector["calldata"]["full"][3:5])
        with self.assertRaisesRegex(ValueError, "serialization differs"):
            oracle.check_abi_agreement(self.abi, [vector])

    def test_changed_domain_or_statement_changes_digest(self):
        original = self.vector["typed_data"]
        for section, field, value in [("domain", "chainId", "11155111"), ("domain", "salt", "0x" + "00" * 32),
                                      ("message", "statement", original["message"]["statement"] + " ")]:
            modified = copy.deepcopy(original)
            modified[section][field] = value
            encoded = oracle.encode_typed_data(full_message=modified)
            digest = oracle.k(b"\x19" + encoded.version + encoded.header + encoded.body)
            self.assertNotEqual(oracle.hx(digest), self.vector["hashes"]["digest"])
            signature = oracle.KEYS.Signature(bytes.fromhex(self.vector["signature"]["v_0_1"][2:]), backend=oracle.KEYS.backend)
            self.assertNotEqual(oracle.KEYS.ecdsa_recover(digest, signature).to_checksum_address(),
                                self.vector["signature"]["recovered_address"])

    def test_unsigned_inputs_and_calldata_cannot_drift(self):
        vectors = [oracle.unsigned_fixture((1, "SN_MAIN", "Starknet Mainnet"), name)
                   for name in ["unlink", "invalidate_pending_incoming"]]
        oracle.check_unsigned_agreement(self.abi, vectors)
        for name in ["unlink", "invalidate_pending_incoming"]:
            for change in ["name", "arity", "type"]:
                abi = copy.deepcopy(self.abi)
                interface = next(entry for entry in abi if entry.get("name") == "contracts::interface::IAddressRegistry")
                method = next(item for item in interface["items"] if item["name"] == name)
                if change == "arity":
                    method["inputs"].append(copy.deepcopy(method["inputs"][0]))
                else:
                    method["inputs"][0][change] = "wrong" if change == "name" else "core::felt252"
                with self.subTest(name=name, change=change), self.assertRaisesRegex(ValueError, "Unsigned entrypoint"):
                    oracle.check_unsigned_agreement(abi, vectors)
        for key, value in [("entrypoint", "stale_name"), ("calldata", ["0"])]:
            changed = copy.deepcopy(vectors)
            changed[0][key] = value
            with self.assertRaisesRegex(ValueError, "Unsigned"):
                oracle.check_unsigned_agreement(self.abi, changed)

    def test_bytearray_boundaries_preserve_all_bytes(self):
        for size in [1, 30, 31, 32, 48]:
            encoded = list(map(int, oracle.byte_array_felts("A" * size)))
            decoded = b"".join(value.to_bytes(31, "big") for value in encoded[1:1 + encoded[0]])
            decoded += encoded[-2].to_bytes(encoded[-1], "big")
            self.assertEqual(decoded, b"A" * size)


if __name__ == "__main__":
    unittest.main()
