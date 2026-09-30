#!/usr/bin/env python3
"""Pruebas del paso «¿Falta esta versión en npm?» de `publicar-plugin.yml`.

El paso es bash dentro del YAML, así que se lo saca del archivo y se lo corre
tal cual, con un `npm` de mentira adelante en el `PATH` que contesta lo que
contestaría el registro. Lo que se mira es lo que el paso decide (`falta`,
`resultado`, el código de salida) y lo que le dice a quien lee la corrida.

Los casos son los de npm 11, medidos contra el registro: una versión que falta
de un paquete que existe da `E404`, igual que un paquete que no existe. Por eso
el mensaje decía «primer publish» al publicar una versión nueva
(Vasak-OS/.github#17).
"""

import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent.parent / ".github/workflows/publicar-plugin.yml"
STEP_NAME = "¿Falta esta versión en npm?"


def step_script() -> str:
    """El `run:` del paso, sin la sangría del YAML.

    Se busca por el nombre del paso y se toma el bloque `run: |` que le sigue
    hasta que la sangría vuelve a bajar. Si el paso cambia de nombre o de forma,
    esto falla nombrándolo, en vez de probar otra cosa.
    """
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == f"- name: {STEP_NAME}")
    run = next(i for i in range(start, len(lines)) if lines[i].strip() == "run: |")
    body_indent = len(lines[run + 1]) - len(lines[run + 1].lstrip())
    body = []
    for line in lines[run + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) < body_indent:
            break
        body.append(line)
    return textwrap.dedent("\n".join(body))


def fake_npm(directory: Path, answers: dict) -> None:
    """Un `npm` que contesta según el argumento de `npm view`.

    `answers` va de lo que se consulta (`paquete@versión` o `paquete`) a
    `(código de salida, salida)`.
    """
    cases = "\n".join(
        f"  {query!r}) printf '%s\\n' {output!r}; exit {code};;"
        for query, (code, output) in answers.items()
    )
    script = directory / "npm"
    script.write_text(
        "#!/bin/sh\n"
        '[ "$1" = view ] || exit 97\n'
        'case "$2" in\n'
        f"{cases}\n"
        "  *) echo \"npm de prueba: consulta inesperada $2\" >&2; exit 98;;\n"
        "esac\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)


E404 = "npm error code E404\nnpm error 404 Not Found"


class NpmQueryStep(unittest.TestCase):
    def run_step(self, answers):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            fake_npm(directory, answers)
            output = directory / "output"
            output.touch()
            env = {
                **os.environ,
                "PATH": f"{directory}:{os.environ['PATH']}",
                "GITHUB_OUTPUT": str(output),
                "NOMBRE": "@vasakgroup/plugin-x",
                "VERSION": "2.1.0",
            }
            done = subprocess.run(
                ["bash", "-e", "-c", step_script()],
                env=env,
                capture_output=True,
                text=True,
            )
            outputs = dict(
                line.split("=", 1) for line in output.read_text().splitlines() if "=" in line
            )
            return done, outputs

    def test_una_version_que_ya_esta_no_se_publica(self):
        done, outputs = self.run_step({"@vasakgroup/plugin-x@2.1.0": (0, "2.1.0")})
        self.assertEqual(done.returncode, 0)
        self.assertEqual(outputs.get("falta"), "no")
        self.assertEqual(outputs.get("resultado"), "ya estaba")

    def test_una_version_nueva_se_dice_version_nueva(self):
        done, outputs = self.run_step(
            {
                "@vasakgroup/plugin-x@2.1.0": (1, E404),
                "@vasakgroup/plugin-x": (0, "@vasakgroup/plugin-x"),
            }
        )
        self.assertEqual(done.returncode, 0)
        self.assertEqual(outputs.get("falta"), "sí")
        self.assertIn("versión nueva", done.stdout)
        self.assertNotIn("primer publish", done.stdout)

    def test_un_paquete_que_no_existe_es_el_primer_publish(self):
        done, outputs = self.run_step(
            {
                "@vasakgroup/plugin-x@2.1.0": (1, E404),
                "@vasakgroup/plugin-x": (1, E404),
            }
        )
        self.assertEqual(done.returncode, 0)
        self.assertEqual(outputs.get("falta"), "sí")
        self.assertIn("primer publish", done.stdout)

    def test_si_no_se_sabe_si_el_paquete_existe_se_publica_igual_y_se_dice(self):
        # La versión falta —eso ya lo contestó el E404—; lo que no se sabe es
        # sólo qué mensaje corresponde.
        done, outputs = self.run_step(
            {
                "@vasakgroup/plugin-x@2.1.0": (1, E404),
                "@vasakgroup/plugin-x": (1, "npm error code E500"),
            }
        )
        self.assertEqual(done.returncode, 0)
        self.assertEqual(outputs.get("falta"), "sí")
        self.assertIn("No se pudo saber", done.stdout)
        self.assertNotIn("primer publish", done.stdout)

    def test_un_error_que_no_es_404_no_se_lee_como_que_falta(self):
        done, outputs = self.run_step({"@vasakgroup/plugin-x@2.1.0": (1, "npm error code E500")})
        self.assertNotEqual(done.returncode, 0)
        self.assertNotIn("falta", outputs)
        self.assertEqual(outputs.get("resultado"), "no se pudo consultar")

    def test_npm_viejo_que_sale_bien_y_vacio_tambien_es_version_nueva(self):
        done, outputs = self.run_step({"@vasakgroup/plugin-x@2.1.0": (0, "")})
        self.assertEqual(done.returncode, 0)
        self.assertEqual(outputs.get("falta"), "sí")
        self.assertIn("versión nueva", done.stdout)


if __name__ == "__main__":
    unittest.main()
