import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_protocol import MODULE, production_registry


class ProductionArtifactsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def index(self, name, modules):
        path = self.root / name
        path.write_text(json.dumps({"contracts": [{"module_path": module} for module in modules]}))
        return path

    def test_registry_is_the_only_production_class(self):
        path = self.index('registry.json', [MODULE])
        self.assertEqual(production_registry([path]), (path, {"module_path": MODULE}))

    def test_other_contract_in_same_or_separate_index_fails(self):
        other = "contracts::OtherContract"
        for indexes in [[self.index('combined.json', [MODULE, other])],
                        [self.index('registry.json', [MODULE]), self.index('sample.json', [other])]]:
            with self.subTest(indexes=indexes), self.assertRaisesRegex(ValueError, 'no other production contract'):
                production_registry(indexes)

    def test_missing_wrong_or_duplicate_registry_fails(self):
        for modules in [[], ["contracts::OtherContract"], [MODULE, MODULE]]:
            with self.subTest(modules=modules), self.assertRaisesRegex(ValueError, 'exactly the registry'):
                production_registry([self.index('invalid.json', modules)])


if __name__ == '__main__':
    unittest.main()
