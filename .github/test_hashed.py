import unittest

from hashed import unhashed

PIN = """asset "tool" {{
    pin {{
        version "{version}"
        url "https://example.com/{{version}}.tar.gz"
        {sha256}
    }}
}}
"""


class Unhashed(unittest.TestCase):
    def test_a_sha256_is_a_hash(self):
        text = PIN.format(version="1.0", sha256='sha256 "' + "a" * 64 + '"')
        self.assertEqual(unhashed(text), [])

    def test_a_full_commit_is_a_hash(self):
        self.assertEqual(unhashed(PIN.format(version="c" * 40, sha256="")), [])

    def test_a_pin_on_one_line_is_unhashed(self):
        text = 'asset "tool" {\n    pin { version "v1"; url "https://x/r.git" }\n}\n'
        self.assertEqual(unhashed(text), ["tool"])

    def test_a_tag_alone_is_unhashed(self):
        self.assertEqual(unhashed(PIN.format(version="B7", sha256="")), ["tool"])


if __name__ == "__main__":
    unittest.main()
