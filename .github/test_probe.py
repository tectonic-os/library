import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from probe import correct, library, main, witnesses

BASE = """schema-version 1

description "A base"

provides {
    "rechunking"
    "ssh" witness="/usr/sbin/sshd"
}

imports "identity"

base "example.invalid/base:$version" {
    family "fedora"
}

option "version" type="string" {
    default "1"
}
"""


class Probe(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cwd = os.getcwd()
        os.chdir(self.temp.name)

    def tearDown(self):
        os.chdir(self.cwd)
        self.temp.cleanup()

    def write(self, path, text):
        directory = Path("components") / path
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "manifest.kdl").write_text(text)

    def measured(self, requires=""):
        self.write("base-image/example", BASE.replace("imports", f"{requires}imports"))
        self.write("identity", 'provides "os-release" witness="/usr/lib/os-release"\n'
                   'imports "helper"\n')
        self.write("helper", 'provides "helper" witness="/usr/bin/helper"\n')
        self.write("tool", 'provides "tool" witness="/usr/bin/tool"\n')
        self.write("deb-tool", 'targets "debian"\nprovides "apt" witness="/usr/bin/apt-get"\n')
        self.write("bootc-base", 'provides "bootc" witness="/usr/bin/bootc"\n')
        bases, components = library()
        return witnesses("base-image/example", bases, components)

    # Every base image ships /usr/lib/os-release. A probe that measured an
    # imported component would ask each base to claim what `identity` provides.
    def test_a_component_the_base_imports_is_never_measured(self):
        self.assertNotIn("os-release", self.measured())
        self.assertNotIn("helper", self.measured())

    def test_a_component_that_meets_a_base_requirement_is_never_measured(self):
        self.assertNotIn("bootc", self.measured('requires "bootc"\n'))
        self.assertNotIn("bootc", self.measured('requires "bootc-base"\n'))

    def test_a_component_for_another_family_is_never_measured(self):
        self.assertNotIn("apt", self.measured())

    def test_the_base_and_a_family_component_are_measured(self):
        self.assertEqual(self.measured(), {
            "ssh": ["/usr/sbin/sshd"],
            "tool": ["/usr/bin/tool"],
            "bootc": ["/usr/bin/bootc"],
        })

    # The consumer's plan measures a key's public half as `<kind>-key`, so the
    # library measures it too, or the consumer reports drift the library
    # never corrects.
    def test_the_public_half_of_a_key_is_measured(self):
        self.write("signing", 'key "cosign" {\n    generator "cosign"\n'
                   '    public "/etc/pki/containers/cosign.pub"\n}\n')
        self.assertEqual(self.measured()["cosign-key"], ["/etc/pki/containers/cosign.pub"])

    def test_a_witness_after_another_property_is_measured(self):
        self.write("shared", 'provides "shared" exclusive=#true witness="/usr/bin/shared"\n')
        self.assertEqual(self.measured()["shared"], ["/usr/bin/shared"])

    def test_list_names_the_image_at_its_version_default(self):
        self.measured()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main(["probe.py", "list"])
        self.assertEqual(out.getvalue(), "base-image/example example.invalid/base:1 "
                         "/usr/bin/bootc /usr/bin/tool /usr/sbin/sshd\n")

    def test_a_base_that_loses_every_name_keeps_no_empty_block(self):
        text = BASE.replace('    "rechunking"\n', "")
        corrected, _ = correct("m", text, {"ssh": ["/usr/sbin/sshd"]}, set())
        self.assertNotIn("provides", corrected)

    def test_a_shipped_name_is_added_and_a_missing_one_removed(self):
        found = {"ssh": ["/usr/sbin/sshd"], "tool": ["/usr/bin/tool"]}
        text, said = correct("m", BASE, found, {"/usr/bin/tool"})
        self.assertIn('provides {\n    "rechunking"\n    "tool" witness="/usr/bin/tool"\n}\n', text)
        self.assertEqual(said, "`m` `provides` loses `ssh` and gains `tool`")

    def test_a_matching_base_is_left_alone(self):
        found = {"ssh": ["/usr/sbin/sshd"]}
        self.assertEqual(correct("m", BASE, found, {"/usr/sbin/sshd"}), (BASE, ""))

    def test_a_base_without_provides_gains_a_block(self):
        text = BASE.replace(BASE[BASE.index("provides"):BASE.index("imports")], "")
        corrected, _ = correct("m", text, {"tool": ["/usr/bin/tool"]}, {"/usr/bin/tool"})
        self.assertIn('provides {\n    "tool" witness="/usr/bin/tool"\n}\n\nimports', corrected)

    def test_a_line_form_provides_is_refused(self):
        text = BASE.replace(BASE[BASE.index("provides"):BASE.index("imports")],
                            'provides "ssh" witness="/usr/sbin/sshd"\n\n')
        with self.assertRaises(SystemExit):
            correct("m", text, {"ssh": ["/usr/sbin/sshd"]}, set())


if __name__ == "__main__":
    unittest.main()
