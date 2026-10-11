import tempfile
import unittest
from pathlib import Path

from closure import row_requires


class RowRequires(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.catalogs = Path(self.temp.name) / "base-images"

    def tearDown(self):
        self.temp.cleanup()

    def write(self, library, name, image, requires=""):
        directory = self.catalogs / library
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{name}.base.kdl").write_text(
            f'base {{\n    image "{image}"\n{requires}}}\n'
        )

    def test_requirements_come_from_the_matching_library_file(self):
        self.write("core", "plain", "example.invalid/plain:1")
        self.write(
            "other",
            "seeded",
            "example.invalid/seeded:1",
            '    requires "bootc-base" "network"\n',
        )

        self.assertEqual(
            row_requires(self.catalogs, "example.invalid/seeded:1"),
            ["bootc-base", "network"],
        )

    def test_a_digest_matches_its_catalogued_tag(self):
        self.write("core", "seeded", "example.invalid/seeded:1")

        self.assertEqual(
            row_requires(self.catalogs, "example.invalid/seeded:1@sha256:abc"), []
        )

    def test_a_missing_base_stops_the_leg(self):
        with self.assertRaisesRegex(SystemExit, "no base file"):
            row_requires(self.catalogs, "example.invalid/missing:1")

    def test_duplicate_descriptions_stop_the_leg(self):
        self.write("core", "one", "example.invalid/duplicate:1")
        self.write("other", "two", "example.invalid/duplicate:1")

        with self.assertRaisesRegex(SystemExit, "more than one base file"):
            row_requires(self.catalogs, "example.invalid/duplicate:1")


if __name__ == "__main__":
    unittest.main()
