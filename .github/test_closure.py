import tempfile
import unittest
from pathlib import Path

from closure import base_needs, close


class BaseNeeds(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.components = Path(self.temp.name) / "components"

    def tearDown(self):
        self.temp.cleanup()

    def write(self, path, image, version=None, requires=""):
        directory = self.components / path
        directory.mkdir(parents=True, exist_ok=True)
        option = ""
        if version is not None:
            option = f'option "version" type="string" {{\n    default "{version}"\n}}\n'
        (directory / "manifest.kdl").write_text(
            f'schema-version 1\n\n{requires}base "{image}" {{\n'
            f'    family "fedora"\n}}\n{option}'
        )

    def test_requirements_come_from_the_base_built_from_the_reference(self):
        self.write("base-image/plain", "example.invalid/plain:$version", "1")
        self.write(
            "base-image/seeded",
            "example.invalid/seeded:$version",
            "1",
            'requires "bootc-base"\nrequires "network"\n',
        )

        self.assertEqual(
            base_needs(self.components, "example.invalid/seeded:1"),
            (["bootc-base", "network"], []),
        )

    def test_a_block_lists_requirements_beside_its_line_form(self):
        self.write(
            "base-image/seeded",
            "example.invalid/seeded:1",
            requires='requires "bootc-base"\nrequires {\n    "network"\n}\n'
            'imports {\n    "identity" { edition "server"; }\n}\n',
        )

        self.assertEqual(
            base_needs(self.components, "example.invalid/seeded:1"),
            (["bootc-base", "network"], ["identity"]),
        )

    def test_the_version_default_is_written_into_the_reference(self):
        self.write("base-image/seeded", "example.invalid/seeded:$version", "2")

        with self.assertRaisesRegex(SystemExit, "no base component"):
            base_needs(self.components, "example.invalid/seeded:1")

    def test_a_component_that_is_not_a_base_is_passed_over(self):
        directory = self.components / "tools"
        directory.mkdir(parents=True)
        (directory / "manifest.kdl").write_text('description "built on example.invalid/tools:1"\n')

        with self.assertRaisesRegex(SystemExit, "no base component"):
            base_needs(self.components, "example.invalid/tools:1")

    def test_a_digest_matches_its_tag(self):
        self.write("base-image/seeded", "example.invalid/seeded:1")

        self.assertEqual(
            base_needs(self.components, "example.invalid/seeded:1@sha256:abc"), ([], [])
        )

    def test_two_bases_on_one_reference_stop_the_leg(self):
        self.write("base-image/one", "example.invalid/duplicate:1")
        self.write("base-image/two", "example.invalid/duplicate:1")

        with self.assertRaisesRegex(SystemExit, "more than one base component"):
            base_needs(self.components, "example.invalid/duplicate:1")


class Close(unittest.TestCase):
    # Each value is (targets, provides, requires, imports), as `read` returns it.
    COMPONENTS = {
        "fedora/build-environment": (set(), {"build-environment"}, set(), set()),
        "identity": (set(), {"os-release"}, set(), set()),
        "deb/bootc-base": (set(), {"bootc-base"}, {"container-runtime"}, set()),
        "deb/container-runtime": (set(), {"container-runtime"}, set(), set()),
        "editor": (set(), {"editor"}, {"build-environment"}, set()),
        "suite": (set(), {"suite"}, set(), {"identity"}),
    }

    def test_an_import_of_the_base_is_never_printed(self):
        needs = ([], ["fedora/build-environment"])
        printed = close(self.COMPONENTS, "fedora", needs, ["editor", "fedora/build-environment"])

        self.assertEqual(printed, ["editor"])

    def test_what_an_import_requires_is_printed(self):
        needs = ([], ["deb/bootc-base"])
        printed = close(self.COMPONENTS, "debian", needs, [])

        self.assertEqual(printed, ["deb/container-runtime"])

    def test_an_import_of_a_printed_component_is_never_printed(self):
        printed = close(self.COMPONENTS, "fedora", ([], []), ["suite"])

        self.assertEqual(printed, ["suite"])


if __name__ == "__main__":
    unittest.main()
