"""El paso «Pruebas de Rust» de `app.yml`, que ahora también mide cobertura.

El paso hace dos cosas con reglas distintas: el color lo deciden las pruebas,
y la cobertura es un subproducto que nunca puede voltearlo. Las dos formas de
equivocarse son silenciosas —un rojo de las pruebas que se traga, o un
problema de cobertura que frena un merge—, así que se prueban las dos.

Se corre **el texto exacto del YAML**, extraído del archivo, con `cargo`
reemplazado por un doble que hace lo que cada caso pide. Y con `bash -e`, que
es como GitHub corre un `run:`.
"""

import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "app.yml"


def extract_step_script(name):
    """El bloque `run: |` del paso con ese nombre, sin la sangría del YAML."""
    lines = WORKFLOW.read_text().splitlines()
    start = lines.index(f"      - name: {name}")
    run = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == "run: |")
    block = []
    for line in lines[run + 1:]:
        if line.strip() and not line.startswith(" " * 10):
            break
        block.append(line)
    return textwrap.dedent("\n".join(block)) + "\n"


# El doble de `cargo`. Lee lo que tiene que hacer de variables de entorno:
#   STUB_LLVMCOV  ok | fail       la corrida instrumentada
#   STUB_TEST     0 | 1           `cargo test` sin instrumentar
#   STUB_LCOV     el informe a escribir, con {raiz} en lugar de la raíz
# y deja en STUB_LOG qué se le pidió, para saber si hubo segunda compilación.
CARGO_STUB = r"""#!/bin/bash
echo "$*" >> "$STUB_LOG"
case "$1" in
  llvm-cov)
    [ "$STUB_LLVMCOV" = ok ] || exit 101
    for a in "$@"; do
      case "$a" in --output-path=*) salida=${a#--output-path=} ;; esac
    done
    printf '%s' "${STUB_LCOV//\{raiz\}/$GITHUB_WORKSPACE}" > "$salida"
    ;;
  test) exit "$STUB_TEST" ;;
  metadata)
    printf '{"packages":[{"name":"demo","manifest_path":"%s/Cargo.toml"}]}' "$GITHUB_WORKSPACE"
    ;;
esac
"""

GOOD_LCOV = "SF:{raiz}/src/lib.rs\nDA:1,1\nDA:2,0\nend_of_record\n"


class RustCoverageStepTest(unittest.TestCase):
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
        self._tool("rustup", "#!/bin/sh\nexit 0\n")
        self._tool("cargo-llvm-cov", "#!/bin/sh\nexit 0\n")
        self.script = base / "step.sh"
        self.script.write_text(extract_step_script("Pruebas de Rust"))

    def tearDown(self):
        self.tmp.cleanup()

    def _tool(self, name, body):
        path = self.bin / name
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IEXEC)

    def run_step(self, llvmcov="ok", test=0, lcov=GOOD_LCOV):
        env = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "HOME": self.tmp.name,
            "GITHUB_WORKSPACE": str(self.repo),
            "PRUEBAS_RUST": "-p demo",
            "STUB_LLVMCOV": llvmcov,
            "STUB_TEST": str(test),
            "STUB_LCOV": lcov,
            "STUB_LOG": str(self.log),
        }
        result = subprocess.run(
            ["bash", "-e", str(self.script)],
            cwd=self.repo, env=env, capture_output=True, text=True,
        )
        return result, self.repo / "coverage" / "rust.lcov"

    def calls(self):
        return self.log.read_text().splitlines()

    def test_measured_run_leaves_relative_report(self):
        """Una corrida medida deja el informe con rutas relativas a la raíz."""
        result, report = self.run_step()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report.read_text().splitlines()[0], "SF:src/lib.rs")
        self.assertIn("1/2 líneas (50.0%)", result.stdout)

    def test_tests_run_once(self):
        """Las pruebas corren una sola vez: sin `cargo test` aparte si la corrida medida pasa."""
        self.run_step()
        self.assertEqual([c.split()[0] for c in self.calls() if c.split()[0] in ("llvm-cov", "test")], ["llvm-cov"])

    def test_red_tests_turn_step_red(self):
        """Pruebas en rojo dejan el paso en rojo, aunque el fallo llegue por la corrida medida."""
        result, report = self.run_step(llvmcov="fail", test=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report.exists())

    def test_coverage_failure_does_not_turn_step_red(self):
        """Si falla sólo la instrumentación, el paso queda en verde y sin informe."""
        result, report = self.run_step(llvmcov="fail", test=0)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(report.exists())
        self.assertIn("lo que falló fue la cobertura", result.stdout)

    def test_without_tool_runs_plain_tests(self):
        """Sin `cargo-llvm-cov` las pruebas corren igual, sin instrumentar, y su rojo cuenta."""
        (self.bin / "cargo-llvm-cov").unlink()
        result, report = self.run_step(test=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report.exists())
        self.assertNotIn("llvm-cov", " ".join(self.calls()))

    def test_report_without_repo_paths_is_deleted(self):
        """Un informe que no nombra nada del repositorio se borra: no es una medición."""
        lcov = "SF:/usr/src/rust/library/std/src/lib.rs\nDA:1,1\nend_of_record\n"
        result, report = self.run_step(lcov=lcov)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(report.exists())

    def test_std_sources_do_not_discard_report(self):
        """Las fuentes de la biblioteca estándar no tumban un informe que sí midió el repositorio."""
        lcov = GOOD_LCOV + "SF:/usr/src/rust/library/std/src/lib.rs\nDA:1,1\nend_of_record\n"
        result, report = self.run_step(lcov=lcov)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SF:src/lib.rs", report.read_text())

    def test_stale_report_is_removed(self):
        """Un informe viejo de otra corrida no sobrevive a una corrida que no midió."""
        (self.repo / "coverage").mkdir()
        (self.repo / "coverage" / "rust.lcov").write_text("SF:viejo.rs\n")
        result, report = self.run_step(llvmcov="fail", test=0)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(report.exists())


class SonarJobTest(unittest.TestCase):
    def test_sonar_waits_for_revisar_and_survives_its_failure(self):
        """`sonar` espera a `revisar`, de donde sale el informe, y corre aunque falle."""
        text = WORKFLOW.read_text()
        job = text[text.index("\n  sonar:\n"):]
        head = job[: job.index("steps:")]
        self.assertIn("needs: revisar", head)
        self.assertIn("if: ${{ !cancelled() }}", head)

    def test_sonar_does_not_compile_rust(self):
        """`sonar` ya no corre `cargo`: la compilación es una sola, en `revisar`."""
        text = WORKFLOW.read_text()
        job = text[text.index("\n  sonar:\n"):]
        self.assertNotIn("cargo llvm-cov", job)
        self.assertNotIn("cargo test", job)

    def test_artifact_name_matches(self):
        """El artefacto que sube `revisar` es el que baja `sonar`."""
        text = WORKFLOW.read_text()
        self.assertEqual(text.count("name: cobertura-rust"), 2)


if __name__ == "__main__":
    unittest.main()
