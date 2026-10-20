"""El paso «El toolchain de Rust» de `app.yml`: falla si `rust-version` supera al stable."""

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_rust_coverage_step import extract_step_script


CARGO_STUB = r"""
case "$1" in
  metadata)
    shift
    sin_deps=no
    manifiesto=
    while [ $# -gt 0 ]; do
      case "$1" in
        --no-deps) sin_deps=si ;;
        --manifest-path) manifiesto=$2; shift ;;
      esac
      shift
    done
    if [ "$sin_deps" != si ] || [ -z "$manifiesto" ]; then
      echo "cargo stub: metadata exige --no-deps y --manifest-path" >&2
      exit 2
    fi
    cat "$manifiesto"
    ;;
  --version)
    echo "cargo __INSTALADA__"
    ;;
  *)
    echo "cargo stub: uso no previsto: $*" >&2
    exit 2
    ;;
esac
"""


def run_step(installed, manifests):
    """`manifests` mapea cada Cargo.toml del repo a su `rust-version` (o None)."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        # El «Cargo.toml» del doble es el JSON que `cargo metadata` devolvería.
        for path, version in manifests.items():
            f = tmp / path
            f.parent.mkdir(parents=True, exist_ok=True)
            valor = f'"{version}"' if version else "null"
            f.write_text('{"packages":[{"rust_version":%s}]}' % valor)
        stubs = {
            "rustup": "exit 0",
            "rustc": f'echo "rustc {installed} (abc 2026-01-01)"',
            "cargo": CARGO_STUB.replace("__INSTALADA__", installed),
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


ROOT = "Cargo.toml"
TAURI = "src-tauri/Cargo.toml"


class ToolchainStepTest(unittest.TestCase):
    def test_falla_si_rust_version_supera_al_instalado(self):
        r = run_step("1.95.0", {ROOT: "1.99.0"})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("rust-version 1.99.0", r.stdout + r.stderr)

    def test_pasa_si_el_instalado_alcanza(self):
        self.assertEqual(run_step("1.99.0", {ROOT: "1.99.0"}).returncode, 0)
        self.assertEqual(run_step("1.99.1", {ROOT: "1.99"}).returncode, 0)

    def test_pasa_si_el_instalado_es_la_version_pedida_sin_parche(self):
        self.assertEqual(run_step("1.99.0", {ROOT: "1.99"}).returncode, 0)

    def test_pasa_sin_rust_version(self):
        self.assertEqual(run_step("1.95.0", {ROOT: None}).returncode, 0)

    def test_falla_con_el_mayor_de_la_raiz_y_de_src_tauri(self):
        r = run_step("1.95.0", {ROOT: "1.90.0", TAURI: "1.99.0"})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("rust-version 1.99.0", r.stdout + r.stderr)

    def test_falla_si_solo_src_tauri_pide_mas_de_lo_instalado(self):
        r = run_step("1.95.0", {TAURI: "1.99.0"})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("rust-version 1.99.0", r.stdout + r.stderr)

    def test_pasa_con_dos_manifiestos_sin_rust_version(self):
        self.assertEqual(run_step("1.95.0", {ROOT: None, TAURI: None}).returncode, 0)


if __name__ == "__main__":
    unittest.main()
