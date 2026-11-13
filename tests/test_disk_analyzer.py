import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from disk_analyzer import scan, yay_path


class DiskAnalyzerTests(unittest.TestCase):
    def test_blocks_hardlinks_and_symlink_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "payload"
            payload.write_bytes(b"x" * 8192)
            os.link(payload, root / "hardlink")
            (root / "loop").symlink_to(root, target_is_directory=True)
            sparse = root / "sparse"
            with sparse.open("wb") as stream:
                stream.truncate(16 * 1024 * 1024)
            expected = sum(path.lstat().st_blocks * 512
                           for path in (root, payload, root / "loop", sparse))
            usage = scan(root)
            self.assertEqual(usage.size, expected)
            self.assertEqual(usage.errors, [])

    def test_missing_is_distinct_from_access_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(scan(Path(directory) / "missing").missing)
            with patch("disk_analyzer.os.scandir", side_effect=PermissionError(
                    13, "Permission denied")):
                usage = scan(Path(directory))
            self.assertFalse(usage.missing)
            self.assertEqual(len(usage.errors), 1)

    def test_yay_custom_build_directory_and_invalid_config(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)
            (config / "yay").mkdir()
            settings = config / "yay/config.json"
            settings.write_text('{"buildDir": "/custom/yay"}')
            warnings = []
            self.assertEqual(yay_path(config, config, warnings), Path("/custom/yay"))
            self.assertEqual(warnings, [])
            settings.write_text("[]")
            self.assertEqual(yay_path(config, config, warnings), config / "yay")
            self.assertEqual(len(warnings), 1)


if __name__ == "__main__":
    unittest.main()
