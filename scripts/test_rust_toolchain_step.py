"""El paso «El toolchain de Rust» de `app.yml`: falla si `rust-version` supera al stable."""

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_rust_coverage_step import extract_step_script


def run_step(rust_version, installed):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        (tmp / "Cargo.toml").write_text("")
        # Dobles: rustup no hace nada, rustc dice la versión, cargo imprime metadata.
        manifest = '{"packages":[{"rust_version":%s}]}' % (
            f'"{rust_version}"' if rust_version else "null"
        )
        stubs = {
            "rustup": "exit 0",
            "rustc": f'echo "rustc {installed} (abc 2026-01-01)"',
            "cargo": f"[ \"$1\" = metadata ] && echo '{manifest}' || echo \"cargo {installed}\"",
        }
        for name, body in stubs.items():
            f = bin_dir / name
            f.write_text("#!/bin/bash\n" + body + "\n")
            f.chmod(f.stat().st_mode | stat.S_IEXEC)
        env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
        return subprocess.run(
            ["bash", "-e", "-c", extract_step_script("El toolchain de Rust")],
            cwd=tmp, env=env, capture_output=True, text=True,
        )


class ToolchainStepTest(unittest.TestCase):
    def test_falla_si_rust_version_supera_al_instalado(self):
        r = run_step("1.99.0", "1.95.0")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("rust-version 1.99.0", r.stdout + r.stderr)

    def test_pasa_si_el_instalado_alcanza(self):
        self.assertEqual(run_step("1.99.0", "1.99.0").returncode, 0)
        self.assertEqual(run_step("1.99", "1.99.1").returncode, 0)

    def test_pasa_sin_rust_version(self):
        self.assertEqual(run_step(None, "1.95.0").returncode, 0)


if __name__ == "__main__":
    unittest.main()
