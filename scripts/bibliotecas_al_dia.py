#!/usr/bin/env python3
"""Avisa cuando una biblioteca propia quedó fuera del alcance de su rango.

En una versión `0.x` el acento **fija la minor**: `^0.7.2` acepta la 0.7.9 y
**no** acepta la 0.8.0. Y un candado que ya satisface el rango no se mueve
solo, así que `bun install` resuelve 0.7.x sin decir nada y la receta empaqueta
con eso.

El resultado es que nada falla. La aplicación compila, pasa sus pruebas y se
publica, y simplemente se queda con los componentes de hace ocho versiones: lo
que se arregla en la biblioteca no llega. Los botones de ventana con el círculo
rojo viajaron así una vez, y el síntoma apareció meses después y en otro lado.

Ya pasó dos veces —en la 0.6 → 0.7 con catorce de dieciséis aplicaciones, y
otra vez después— y las dos se arreglaron a mano. Que se vuelva a partir en el
mismo lugar es la señal de que el arreglo a mano no era el arreglo.

Sólo mira las propias. Una dependencia de terceros atrasada suele ser una
decisión —subir una mayor rompe cosas— mientras que quedarse atrás en la
nuestra no lo decide nadie: pasa.
"""

import argparse
import json
import re
import sys
import urllib.request

PROPIAS = "@vasakgroup/"
REGISTRO = "https://registry.npmjs.org/"


def partes(version):
    """Los tres números de una versión, o nada si no tiene esa forma."""
    encontrado = re.match(r"(\d+)\.(\d+)\.(\d+)", version or "")
    return tuple(int(x) for x in encontrado.groups()) if encontrado else None


def alcanza(rango, ultima):
    """Si el rango declarado puede llegar a resolver a `ultima`.

    Lo que no tiene forma de rango de versión —`git://`, `workspace:`, `*`— se
    da por alcanzable: no es algo que este guardia pueda ni deba juzgar.
    """
    destino = partes(ultima)
    declarado = re.match(r"^([\^~]?)v?(\d+)\.(\d+)\.(\d+)", (rango or "").strip())
    if destino is None or declarado is None:
        return True

    acento = declarado.group(1)
    mayor, minor, parche = (int(x) for x in declarado.groups()[1:])

    # El piso, antes que el techo. Un rango no sólo tiene un tope: `^0.7.2` no
    # acepta la 0.7.1 aunque compartan la minor. Pasa cuando el rango declara
    # algo más nuevo que lo publicado —una versión que se dio de baja, o un
    # número que se subió antes de publicarlo— y sin esto el guardia se queda
    # callado justo ahí, que es un estado que alguien debería mirar.
    if partes(ultima) < (mayor, minor, parche):
        return False

    if acento == "^":
        if mayor == 0 and minor == 0:
            return destino == (0, 0, parche)      # ^0.0.x fija el parche
        if mayor == 0:
            return destino[0] == 0 and destino[1] == minor   # ^0.x fija la minor
        return destino[0] == mayor                            # ^X.y fija la mayor
    if acento == "~":
        return destino[0] == mayor and destino[1] == minor
    return destino == (mayor, minor, parche)                  # exacta


def declaradas(manifiesto):
    """Lo que el `package.json` pide, de las dos secciones juntas."""
    todas = {}
    for seccion in ("dependencies", "devDependencies"):
        todas.update(manifiesto.get(seccion, {}))
    return todas


def ultima_publicada(nombre):
    """La versión que el registro marca como `latest`.

    Va por `dist-tags` y no por el atajo `/latest`, que la CDN sirve cacheado y
    puede contestar una versión vieja — pasó al medir esto a mano.
    """
    url = REGISTRO + nombre.replace("/", "%2f")
    with urllib.request.urlopen(url, timeout=20) as respuesta:
        return json.load(respuesta)["dist-tags"]["latest"]


def revisar(manifiesto, consultar=None):
    """Las propias que quedaron fuera de alcance, y las que no se pudieron ver.

    `consultar` se puede reemplazar para probar esto sin red. Se resuelve acá
    adentro y no en la firma a propósito: un valor por omisión se fija cuando
    se define la función, así que reemplazar `ultima_publicada` en el módulo no
    habría tenido efecto y la prueba habría salido a la red creyendo que no.
    Pasó.
    """
    if consultar is None:
        consultar = ultima_publicada

    atrasadas, sin_respuesta = [], []

    for nombre, rango in sorted(declaradas(manifiesto).items()):
        if not nombre.startswith(PROPIAS):
            continue
        try:
            ultima = consultar(nombre)
        except Exception as error:
            sin_respuesta.append((nombre, str(error)))
            continue
        if not alcanza(rango, ultima):
            atrasadas.append((nombre, rango, ultima))

    return atrasadas, sin_respuesta


def main(argv=None):
    opciones = argparse.ArgumentParser(description=__doc__)
    opciones.add_argument("--manifiesto", default="package.json")
    opciones.add_argument(
        "--cortar",
        action="store_true",
        help="Salir con error en vez de sólo avisar.",
    )
    elegido = opciones.parse_args(argv)

    try:
        with open(elegido.manifiesto, encoding="utf-8") as archivo:
            manifiesto = json.load(archivo)
    except FileNotFoundError:
        print(f"No hay {elegido.manifiesto}; no hay nada que comprobar.")
        return 0

    atrasadas, sin_respuesta = revisar(manifiesto)

    for nombre, motivo in sin_respuesta:
        # El registro caído no puede cortar la corrida: no dice nada sobre el
        # código del PR.
        print(f"::warning::No se pudo consultar {nombre} ({motivo}); no se comprobó.")

    if not atrasadas:
        if sin_respuesta:
            # Decir «están al día» después de avisar que una no se pudo
            # consultar es afirmar algo que no se comprobó, y las dos líneas
            # juntas se contradicen: se lee la segunda y se olvida la primera.
            print("Ninguna de las que se pudieron consultar está atrasada.")
        else:
            print("Las bibliotecas propias están al día.")
        return 0

    for nombre, rango, ultima in atrasadas:
        print(
            f"::warning::{nombre} declara {rango} y la última publicada es "
            f"{ultima}. El rango no puede llegar: hay que subirlo a mano."
        )

    return 1 if elegido.cortar else 0


if __name__ == "__main__":
    sys.exit(main())
