#!/usr/bin/env python3
"""Comprueba que la etiqueta del release y el bundle vayan a decir lo mismo.

El `.deb` que produce Tauri se llama con la versión de `tauri.conf.json`, no con
la etiqueta que disparó el release. Cuando las dos se separan hay dos formas de
terminar mal y ninguna se ve venir:

1. **El release queda vacío.** Se compila, el paso que busca
   `vasak-text_0.4.0_amd64.deb` no lo encuentra porque el archivo se llama
   `0.3.0`, y lo que se publicó es una etiqueta sin nada colgando.
2. **El release queda mintiendo.** Peor: si el paso subiera lo que encuentre sin
   mirar, `v0.4.0` tendría adentro un paquete 0.3.0, y quien lo baje instala una
   versión distinta de la que dice el release.

Al PKGBUILD ya le pasó lo mismo por el otro lado —`pkgver` contra la versión del
bundle— y su comentario dice lo que cuesta: «una compilación que llegó hasta acá
ya gastó varios minutos». Por eso esto corre **antes** de compilar, que es
cuando enterarse es gratis: son dos archivos y cinco segundos contra media hora
de runner.

Que los manifiestos coincidan **entre sí** no se mira acá: eso ya lo comprueba
el paso «Los manifiestos dicen la misma versión» de `app.yml` en cada PR. Lo que
nadie miraba es la etiqueta, que no está en ningún manifiesto y se escribe a
mano en el momento de publicar.

**Dónde vive la versión no es una sola cosa**, y por eso la búsqueda tiene
cuatro escalones en vez de abrir un archivo. Tauri la acepta escrita de tres
formas —el número, una ruta a un `package.json`, o nada y la hereda de Cargo— y
encima la configuración de Linux puede pisar a la base. Cargo suma la suya: en
un workspace el miembro dice `version.workspace = true` y el número está en
`[workspace.package]` de la raíz, que es como están `vasak-store` y
`vasak-permissions`. Equivocarse en cualquiera de esos escalones no se ve: el
guardia diría que no sabe qué versión es y cortaría un release perfectamente
válido.
"""

import argparse
import json
import os
import re
import sys
import tomllib
from pathlib import Path

LINUX_CONF = Path("src-tauri/tauri.linux.conf.json")
TAURI_CONF = Path("src-tauri/tauri.conf.json")
TAURI_CARGO = Path("src-tauri/Cargo.toml")
ROOT_CARGO = Path("Cargo.toml")


def strip_prefix(tag: str) -> str:
    """Saca la `v` de `v0.4.0`.

    Las dos formas conviven en el taller —`vasak-desktop` tiene etiquetas con
    prefijo y sin él—, así que aceptar una sola dejaría media docena de
    repositorios sin poder publicar por un motivo que no es el suyo.
    """
    return tag[1:] if re.fullmatch(r"v\d.*", tag) else tag


def json_version(path: Path) -> str | None:
    """La versión que declara un `tauri.conf.json`, o None si no declara.

    `version` puede ser el número **o una ruta a un `package.json`**, que es una
    forma que Tauri acepta y que acá se leería como si la versión fuese
    `"../package.json"`: el guardia compararía la etiqueta contra el texto de
    una ruta y cortaría un release que estaba bien.
    """
    if not path.is_file():
        return None
    try:
        declared = json.loads(path.read_text(encoding="utf-8")).get("version")
    except json.JSONDecodeError as error:
        print(f"::error::{path} no se pudo leer: {error}")
        return None

    if not isinstance(declared, str) or not declared:
        return None
    if not declared.endswith(".json"):
        return declared

    # La ruta es relativa al archivo que la nombra, no al directorio desde el
    # que corre esto.
    target = path.parent / declared
    if not target.is_file():
        print(f"::error::{path} apunta a {declared} y ese archivo no está.")
        return None
    try:
        pointed = json.loads(target.read_text(encoding="utf-8")).get("version")
    except json.JSONDecodeError as error:
        print(f"::error::{target} no se pudo leer: {error}")
        return None
    return pointed if isinstance(pointed, str) and pointed else None


def cargo_version(path: Path) -> str | None:
    """La versión de un Cargo.toml, o None si la hereda del workspace.

    Mira las dos tablas donde puede estar. `[package]` es la del miembro, y
    `[workspace.package]` la que heredan los miembros que dicen
    `version.workspace = true` — un workspace virtual, como los de
    `vasak-store` y `vasak-permissions`, **no tiene `[package]`** y leer sólo
    ésa devolvería que no hay versión en un repositorio que la tiene.
    """
    if not path.is_file():
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        print(f"::error::No se pudo leer {path}: {error}")
        return None

    # `version.workspace = true` se lee como un diccionario, no como un número:
    # devolverlo tal cual haría que la comparación fallara diciendo que la
    # etiqueta no coincide con `{'workspace': True}`, que no ayuda a nadie.
    own = data.get("package", {}).get("version")
    if isinstance(own, str) and own:
        return own

    shared = data.get("workspace", {}).get("package", {}).get("version")
    return shared if isinstance(shared, str) and shared else None


def bundled_version(root: Path) -> tuple[str | None, str]:
    """La versión con la que va a quedar nombrado el `.deb`, y de dónde sale.

    El orden es el de Tauri: la configuración de Linux pisa a la base, manda el
    JSON, y cuando no declara `version` se cae al `Cargo.toml` de `src-tauri` y
    de ahí a la raíz. Copiarlo importa porque un repositorio que no declare la
    versión en el JSON no está roto —Tauri compila igual— y cortar ahí sería
    inventar una regla que Tauri no tiene.
    """
    for candidate in (LINUX_CONF, TAURI_CONF):
        version = json_version(root / candidate)
        if version:
            return version, str(candidate)

    for candidate in (TAURI_CARGO, ROOT_CARGO):
        version = cargo_version(root / candidate)
        if version:
            return version, str(candidate)

    return None, "ni tauri.conf.json ni Cargo.toml declaran una versión"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="La etiqueta del release.")
    parser.add_argument("--root", default=".", help="La raíz del repositorio.")
    chosen = parser.parse_args()

    root = Path(chosen.root)
    version, source = bundled_version(root)
    if version is None:
        print(f"::error::No se sabe qué versión va a llevar el bundle: {source}")
        return 1

    wanted = strip_prefix(chosen.tag)
    if wanted != version:
        print(
            f"::error::El release se etiquetó «{chosen.tag}» y {source} dice "
            f"«{version}». El .deb se llamaría con la segunda, así que no se "
            f"compila: o la etiqueta está mal, o falta subir la versión."
        )
        return 1

    print(f"La etiqueta y {source} dicen {version}.")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"version={version}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
