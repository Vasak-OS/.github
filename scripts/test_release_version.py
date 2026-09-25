#!/usr/bin/env python3
"""Pruebas de `release_version.py`.

Lo que se prueba acá es sobre todo que **no diga que sí** cuando no debe: el
guardia corre justo antes de media hora de compilación y su único trabajo es
cortar, así que un falso «coinciden» se ve exactamente igual que estar todo
bien —un release verde— y se descubre cuando alguien baja el paquete.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import release_version


def build_repo(directory, *, tauri=None, tauri_cargo=None, root_cargo=None):
    """Arma un repositorio de mentira con sólo los manifiestos que se le pidan."""
    root = Path(directory)
    if tauri is not None:
        (root / "src-tauri").mkdir(parents=True, exist_ok=True)
        (root / "src-tauri/tauri.conf.json").write_text(json.dumps(tauri))
    if tauri_cargo is not None:
        (root / "src-tauri").mkdir(parents=True, exist_ok=True)
        (root / "src-tauri/Cargo.toml").write_text(tauri_cargo)
    if root_cargo is not None:
        (root / "Cargo.toml").write_text(root_cargo)
    return root


class TestStripPrefix(unittest.TestCase):
    def test_saca_la_v_del_prefijo(self):
        self.assertEqual(release_version.strip_prefix("v0.4.0"), "0.4.0")

    def test_deja_la_etiqueta_sin_prefijo(self):
        self.assertEqual(release_version.strip_prefix("0.4.0"), "0.4.0")

    def test_no_muerde_una_version_que_empieza_con_letra(self):
        # `version-0.4.0` no es «v» + número: sacarle la primera letra daría
        # `ersion-0.4.0` y el mensaje de error hablaría de algo que nadie
        # escribió.
        self.assertEqual(
            release_version.strip_prefix("version-0.4.0"), "version-0.4.0"
        )


class TestBundledVersion(unittest.TestCase):
    def test_manda_tauri_conf(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_repo(
                directory,
                tauri={"version": "0.4.0"},
                tauri_cargo='[package]\nname = "x"\nversion = "9.9.9"\n',
            )
            version, source = release_version.bundled_version(root)
            self.assertEqual(version, "0.4.0")
            self.assertIn("tauri.conf.json", source)

    def test_cae_al_cargo_de_src_tauri(self):
        # Un repositorio que no declara la versión en el JSON no está roto:
        # Tauri la toma de Cargo.toml y compila igual.
        with tempfile.TemporaryDirectory() as directory:
            root = build_repo(
                directory,
                tauri={"productName": "x"},
                tauri_cargo='[package]\nname = "x"\nversion = "0.4.0"\n',
            )
            version, source = release_version.bundled_version(root)
            self.assertEqual(version, "0.4.0")
            self.assertIn("Cargo.toml", source)

    def test_cae_al_cargo_de_la_raiz_cuando_hereda_del_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_repo(
                directory,
                tauri={},
                tauri_cargo='[package]\nname = "x"\nversion.workspace = true\n',
                root_cargo='[package]\nname = "w"\nversion = "1.2.3"\n',
            )
            version, _ = release_version.bundled_version(root)
            self.assertEqual(version, "1.2.3")

    def test_sin_manifiestos_no_inventa_una_version(self):
        with tempfile.TemporaryDirectory() as directory:
            version, _ = release_version.bundled_version(Path(directory))
            self.assertIsNone(version)

    def test_un_json_roto_no_pasa_por_bueno(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src-tauri").mkdir()
            (root / "src-tauri/tauri.conf.json").write_text("{ esto no es json")
            version, _ = release_version.bundled_version(root)
            self.assertIsNone(version)


class TestMain(unittest.TestCase):
    def run_main(self, root, tag, output=None):
        argv = ["--tag", tag, "--root", str(root)]
        previous = os.environ.get("GITHUB_OUTPUT")
        if output is not None:
            os.environ["GITHUB_OUTPUT"] = str(output)
        else:
            os.environ.pop("GITHUB_OUTPUT", None)
        try:
            saved = sys.argv
            sys.argv = ["release_version.py", *argv]
            return release_version.main()
        finally:
            sys.argv = saved
            if previous is None:
                os.environ.pop("GITHUB_OUTPUT", None)
            else:
                os.environ["GITHUB_OUTPUT"] = previous

    def test_coinciden(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_repo(directory, tauri={"version": "0.4.0"})
            self.assertEqual(self.run_main(root, "v0.4.0"), 0)

    def test_no_coinciden(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_repo(directory, tauri={"version": "0.3.0"})
            self.assertEqual(self.run_main(root, "v0.4.0"), 1)

    def test_una_version_mas_larga_no_cuenta_como_igual(self):
        # `v0.4.0-rc1` contra `0.4.0`: el bundle se llamaría `0.4.0` y el
        # release diría otra cosa.
        with tempfile.TemporaryDirectory() as directory:
            root = build_repo(directory, tauri={"version": "0.4.0"})
            self.assertEqual(self.run_main(root, "v0.4.0-rc1"), 1)

    def test_sin_manifiestos_corta(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(self.run_main(Path(directory), "v0.4.0"), 1)

    def test_emite_la_version_para_el_paso_siguiente(self):
        with tempfile.TemporaryDirectory() as directory:
            root = build_repo(directory, tauri={"version": "0.4.0"})
            output = Path(directory) / "salida"
            output.write_text("")
            self.assertEqual(self.run_main(root, "v0.4.0", output), 0)
            self.assertIn("version=0.4.0", output.read_text())


if __name__ == "__main__":
    unittest.main()
