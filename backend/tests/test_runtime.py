import sys
import unittest

import app  # noqa: F401 - importing app applies the shared console configuration


class RuntimeEncodingTests(unittest.TestCase):
    def test_application_streams_use_utf8(self):
        self.assertEqual(sys.stdout.encoding.lower().replace("-", ""), "utf8")
        self.assertEqual(sys.stderr.encoding.lower().replace("-", ""), "utf8")

    def test_unicode_logs_can_be_written(self):
        print("[RuntimeTest] Tiếng Việt → UTF-8")


if __name__ == "__main__":
    unittest.main()
