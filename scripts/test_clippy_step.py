"""El paso «Los avisos de clippy» de `app.yml`.

El paso decide entre tres desenlaces según dos datos —si clippy tiene avisos y
si `clippy_corta` está encendido—, y un cuarto cuando clippy ni se puede
instalar. Equivocarse acá es silencioso: una puerta que nunca corta, o un
repositorio rojo por un componente que no se instaló.

Se corre **el texto exacto del YAML**, extraído del archivo, con `rustup` y
`cargo` reemplazados por dobles, y con `bash -e`, que es como GitHub corre un
`run:`.
"""

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_rust_coverage_step import extract_step_script

# `cargo clippy` sale con STUB_CLIPPY (0 = sin avisos); deja en STUB_LOG qué se
# le pidió y desde qué directorio, para saber si corrió y dónde.
CARGO_STUB = r"""#!/bin/bash
echo "$PWD: $*" >> "$STUB_LOG"
[ "$1" = clippy ] && exit "$STUB_CLIPPY"
exit 0
"""


class ClippyStepTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.repo = base / "repo"
        self.repo.mkdir()
        (self.repo / "Cargo.toml").write_text('[package]\nname = "demo"\n')
        self.bin = base / "bin"
        self.bin.mkdir()
        self.log = base / "cargo.log"
        self.log.write_text("")
        self._tool("cargo", CARGO_STUB)
        self._tool("rustup", '#!/bin/sh\nexit "$STUB_RUSTUP"\n')
        self.script = base / "step.sh"
        self.script.write_text(extract_step_script("Los avisos de clippy"))

    def tearDown(self):
        self.tmp.cleanup()

    def _tool(self, name, body):
        path = self.bin / name
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IEXEC)

    def run_step(self, clippy=0, corta="false", rustup=0):
        env = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "HOME": self.tmp.name,
            "PRUEBAS_RUST": "-p demo -p otro",
            "CORTA": corta,
            "STUB_CLIPPY": str(clippy),
            "STUB_RUSTUP": str(rustup),
            "STUB_LOG": str(self.log),
        }
        return subprocess.run(
            ["bash", "-e", str(self.script)],
            cwd=self.repo, env=env, capture_output=True, text=True,
        )

    def calls(self):
        return self.log.read_text().splitlines()

    def test_clean_clippy_passes(self):
        """Sin avisos el paso sale en verde y lo dice."""
        result = self.run_step(clippy=0)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("clippy no tiene avisos.", result.stdout)
        self.assertNotIn("::warning::", result.stdout)

    def test_clippy_gets_crates_and_deny_warnings(self):
        """Clippy recibe cada crate como argumento separado, `--locked`, `--all-targets` y `-D warnings`."""
        self.run_step()
        self.assertEqual(
            self.calls(),
            [f"{self.repo.resolve()}: clippy --locked --all-targets -p demo -p otro -- -D warnings"],
        )

    def test_warnings_do_not_cut_when_gate_is_off(self):
        """Con avisos y la puerta apagada el paso sigue en verde y deja un `::warning::`."""
        result = self.run_step(clippy=101, corta="false")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("::warning::clippy tiene avisos", result.stdout)
        self.assertNotIn("::error::", result.stdout)

    def test_warnings_cut_when_gate_is_on(self):
        """Con avisos y la puerta encendida el paso sale en rojo con un `::error::`."""
        result = self.run_step(clippy=101, corta="true")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("::error::clippy tiene avisos", result.stdout)

    def test_clean_clippy_passes_even_with_gate_on(self):
        """La puerta encendida no corta si clippy no tiene avisos."""
        result = self.run_step(clippy=0, corta="true")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_component_warns_and_does_not_run_clippy(self):
        """Si clippy no se puede instalar el paso avisa, sale en verde y no corre `cargo clippy`."""
        result = self.run_step(rustup=1, clippy=101, corta="true")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("::warning::No se pudo instalar clippy", result.stdout)
        self.assertEqual(self.calls(), [])

    def test_runs_inside_src_tauri_when_there_is_no_root_manifest(self):
        """Sin `Cargo.toml` en la raíz y con `src-tauri/Cargo.toml`, clippy corre dentro de `src-tauri`."""
        (self.repo / "Cargo.toml").unlink()
        (self.repo / "src-tauri").mkdir()
        (self.repo / "src-tauri" / "Cargo.toml").write_text('[package]\nname = "demo"\n')
        result = self.run_step()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.calls()[0].startswith(f"{(self.repo / 'src-tauri').resolve()}: clippy"), self.calls())


if __name__ == "__main__":
    unittest.main()
