"""Run the identity finalize hook against a temporary os-release.

    python3 -m unittest discover -s components/identity
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).with_name("finalize.sh")

# Fedora ships os-release as a symlink into os.release.d.
# run_hook makes that link unless a test asks for regular files.
FEDORA = 'NAME="Fedora Linux"\nVERSION_ID=44\nID=fedora\nPRETTY_NAME="Fedora Linux 44"\n'


class IdentityHook(unittest.TestCase):
    def run_hook(self, regular=False, **env):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "usr/lib/os.release.d").mkdir(parents=True)
            (root / "etc").mkdir()
            (root / "usr/lib/os.release.d/os-release-fedora").write_text(FEDORA)
            if regular:
                (root / "usr/lib/os-release").write_text(FEDORA)
                (root / "etc/os-release").write_text(FEDORA)
            else:
                (root / "usr/lib/os-release").symlink_to("os.release.d/os-release-fedora")
            script = HOOK.read_text().replace(
                "local file=/usr/lib/os-release", f"local file={root}/usr/lib/os-release"
            ).replace("local link=/etc/os-release", f"local link={root}/etc/os-release")
            # An unmatched path would let the hook rewrite the host's own os-release.
            self.assertNotIn("=/usr/lib/os-release", script)
            self.assertNotIn("=/etc/os-release", script)
            ran = subprocess.run(
                ["bash", "-euo", "pipefail", "-c", script],
                env={"PATH": os.environ["PATH"], **env},
                capture_output=True,
                text=True,
            )
            written = root / "usr/lib/os-release"
            if ran.returncode != 0:
                return ran, None, None
            return ran, written.read_text(), (written.is_symlink(), (root / "etc/os-release").resolve() == written)

    def test_keys_are_replaced_in_place_and_absent_ones_appended(self):
        _, text, (symlink, linked) = self.run_hook(
            IMAGE_NAME="Workstation", IMAGE_ID="workstation", IMAGE_VERSION="20261028"
        )
        self.assertEqual(
            text,
            'NAME="Workstation"\nVERSION_ID=44\nID=fedora\nPRETTY_NAME="Workstation 20261028"\n'
            'DEFAULT_HOSTNAME="workstation"\nIMAGE_VERSION="20261028"\n',
        )
        # A rewrite through the symlink would change the os.release.d copy too.
        self.assertFalse(symlink)
        self.assertTrue(linked)

    def test_regular_files_are_rewritten_and_etc_becomes_a_link(self):
        _, text, (symlink, linked) = self.run_hook(
            regular=True, IMAGE_NAME="Workstation", IMAGE_ID="workstation"
        )
        self.assertIn('NAME="Workstation"\n', text)
        self.assertFalse(symlink)
        self.assertTrue(linked)

    def test_declared_values_are_quoted_and_the_urls_set(self):
        _, text, _ = self.run_hook(
            IMAGE_NAME="Workstation",
            IMAGE_ID="workstation",
            IMAGE_PRETTY_NAME='The "$HOME" box',
            IMAGE_URL="https://example.org",
            IMAGE_ISSUES_URL="https://example.org/issues",
        )
        self.assertIn('PRETTY_NAME="The \\"\\$HOME\\" box"\n', text)
        self.assertIn('IMAGE_VERSION="dev"\n', text)
        self.assertIn('HOME_URL="https://example.org"\n', text)
        self.assertIn('BUG_REPORT_URL="https://example.org/issues"\n', text)

    def test_an_image_without_a_name_fails_naming_the_variable(self):
        ran, _, _ = self.run_hook(IMAGE_ID="workstation")
        self.assertNotEqual(ran.returncode, 0)
        self.assertIn("IMAGE_NAME", ran.stderr)


if __name__ == "__main__":
    unittest.main()
