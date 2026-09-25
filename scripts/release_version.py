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
"""

import argparse
import json
import os
import re
import sys
import tomllib
from pathlib import Path

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


def cargo_version(path: Path) -> str | None:
    """La versión de un Cargo.toml, o None si la hereda del workspace."""
    if not path.is_file():
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        print(f"::error::No se pudo leer {path}: {error}")
        return None
    version = data.get("package", {}).get("version")
    # `version.workspace = true` se lee como un diccionario, no como un número:
    # devolverlo tal cual haría que la comparación de abajo fallara diciendo que
    # la etiqueta no coincide con `{'workspace': True}`, que no ayuda a nadie.
    return version if isinstance(version, str) else None


def bundled_version(root: Path) -> tuple[str | None, str]:
    """La versión con la que va a quedar nombrado el `.deb`, y de dónde sale.

    El orden es el de Tauri: manda `tauri.conf.json`, y cuando no declara
    `version` cae al `Cargo.toml` de `src-tauri`. Copiarlo importa porque un
    repositorio que no declare la versión en el JSON no está roto —Tauri
    compila igual— y cortar ahí sería inventar una regla que Tauri no tiene.
    """
    conf = root / TAURI_CONF
    if conf.is_file():
        try:
            declared = json.loads(conf.read_text(encoding="utf-8")).get("version")
        except json.JSONDecodeError as error:
            return None, f"{TAURI_CONF} no se pudo leer: {error}"
        if isinstance(declared, str) and declared:
            return declared, str(TAURI_CONF)

    for candidate in (root / TAURI_CARGO, root / ROOT_CARGO):
        version = cargo_version(candidate)
        if version:
            return version, str(candidate.relative_to(root))

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
