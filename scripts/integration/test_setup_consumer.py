import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from setup_consumer_typescript import claim, verified_members, verify


class CompilerInstallerTests(unittest.TestCase):
    def test_unmanaged_and_symlink_destinations_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "unmanaged"):
                claim(root)
            link = root / "link"
            link.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                claim(link)
            managed = root / "managed"
            claim(managed)
            claim(managed)

    def test_bad_integrity_rejected(self):
        with self.assertRaisesRegex(ValueError, "integrity"):
            verify(b"wrong bytes", "sha512-wrong")

    def test_traversal_and_links_rejected(self):
        for name, kind in [("package/../../escape", tarfile.REGTYPE),
                           ("/absolute", tarfile.REGTYPE),
                           ("package/link", tarfile.SYMTYPE)]:
            with self.subTest(name=name):
                stream = io.BytesIO()
                with tarfile.open(fileobj=stream, mode="w") as archive:
                    entry = tarfile.TarInfo(name)
                    entry.type = kind
                    archive.addfile(entry)
                stream.seek(0)
                with tarfile.open(fileobj=stream) as archive:
                    with self.assertRaisesRegex(ValueError, "Unsafe"):
                        verified_members(archive)


if __name__ == "__main__":
    unittest.main()
