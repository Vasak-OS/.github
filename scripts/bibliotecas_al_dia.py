#!/usr/bin/env python3
"""Avisa cuando una biblioteca propia no es la que se va a empaquetar.

Son **dos** formas de quedarse atrás y el arreglo de cada una es distinto:

1. **El rango no alcanza.** En una versión `0.x` el acento fija la minor:
   `^0.7.2` acepta la 0.7.9 y **no** acepta la 0.8.0. Hay que editar el
   `package.json`.
2. **El rango alcanza y el candado no se movió.** `^1.0.0` sí admite la 1.4.0,
   pero un candado que ya satisface el rango **no se mueve solo**: `bun install`
   resuelve la 1.0.0 sin decir nada y la receta empaqueta con eso. Alcanza con
   `bun update`.

La segunda es la más silenciosa: el rango está bien escrito y no hay ningún
archivo que mirar y encontrar mal. Este guardia miró sólo la primera hasta que
el barrido del 2026-09-22 encontró once repositorios atrasados **con el guardia
en verde** —y uno de ellos había migrado setenta y un iconos a un componente
cuatro minors viejo sin enterarse—.

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

#: Una entrada de la sección de paquetes de `bun.lock`:
#: ``"nombre": ["nombre@1.2.3", "", { ... }, "sha512-..."],``
#: La clave con barra —``"a/b"``— es una copia anidada, no la del árbol de
#: arriba, y por eso se exige que sea igual al nombre del paquete.
ENTRADA_DEL_CANDADO = re.compile(
    r'^\s*"(?P<clave>[^"]+)":\s*\[\s*"(?P<resuelto>[^"]+)"', re.MULTILINE
)


def partes(version):
    """Los tres números de una versión, o nada si no tiene esa forma."""
    encontrado = re.match(r"(\d+)\.(\d+)\.(\d+)", version or "")
    return tuple(int(x) for x in encontrado.groups()) if encontrado else None


def es_preliberacion(version):
    """Si la versión trae etiqueta de preliberación: `1.4.0-beta.1`.

    `partes()` se queda con los tres números y tira lo que sigue, así que la
    `1.4.0-beta.1` y la `1.4.0-beta.2` le salen iguales. Comparar dos
    preliberaciones bien es implementar la precedencia de SemVer entera
    —identificadores numéricos contra alfanuméricos, el que tiene menos campos
    gana, y una preliberación va antes que su versión final— y ninguno de los
    diez paquetes propios publicó una nunca: 81 versiones, cero con guion.

    Así que en vez de adivinar, no se compara y se dice. Es el mismo criterio
    que con el registro caído y con el candado que no está: este guardia
    existe para no afirmar lo que no comprobó, y contestar «al día» sobre dos
    versiones que no sabe ordenar sería justamente eso. El día que aparezca
    una preliberación el aviso va a estar, con el caso de verdad delante.
    """
    return bool(re.match(r"\d+\.\d+\.\d+-", (version or "").strip()))


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


def resueltas(candado):
    """Qué versión quedó fijada para cada paquete, según el texto de `bun.lock`.

    Se lee con una expresión regular y no con `json.load` porque el candado de
    bun lleva comas finales: es JSON para leer, no para parsear.

    Sólo entran las entradas cuya clave es **exactamente** el nombre del
    paquete. Una clave con barra —``"vite/esbuild"``— es una copia anidada que
    convive con la de arriba, y tomarla sería informar una versión que no es la
    que usa la aplicación.
    """
    fijadas = {}
    for entrada in ENTRADA_DEL_CANDADO.finditer(candado or ""):
        clave, resuelto = entrada.group("clave"), entrada.group("resuelto")
        nombre, _, version = resuelto.rpartition("@")
        # `rpartition` sobre `@scope/paquete` sin versión deja el nombre vacío:
        # pasa con los enlaces al espacio de trabajo, que no tienen versión que
        # comprobar.
        if nombre == clave and partes(version):
            fijadas[clave] = version
    return fijadas


def ultima_publicada(nombre):
    """La versión que el registro marca como `latest`.

    Va por `dist-tags` y no por el atajo `/latest`, que la CDN sirve cacheado y
    puede contestar una versión vieja — pasó al medir esto a mano.
    """
    url = REGISTRO + nombre.replace("/", "%2f")
    with urllib.request.urlopen(url, timeout=20) as respuesta:
        return json.load(respuesta)["dist-tags"]["latest"]


def revisar(manifiesto, fijadas=None, consultar=None):
    """Las propias que no son la última, separadas por qué hay que hacerles.

    Devuelve cuatro listas: las que el **rango** no puede alcanzar, las que el
    rango alcanza pero el **candado** dejó atrás, las que no se pudieron
    ordenar porque hay una preliberación de por medio, y las que no se
    pudieron consultar. Son tres cosas distintas y el aviso de cada una es distinto:
    la primera se arregla editando el manifiesto, la segunda con `bun update`,
    y la tercera no se arregla, se vuelve a intentar.

    Una que está fuera de rango **no** se cuenta además como candado atrasado:
    es la misma biblioteca y el mismo arreglo, y decirlo dos veces con dos
    instrucciones distintas confunde cuál seguir.

    `consultar` se puede reemplazar para probar esto sin red. Se resuelve acá
    adentro y no en la firma a propósito: un valor por omisión se fija cuando
    se define la función, así que reemplazar `ultima_publicada` en el módulo no
    habría tenido efecto y la prueba habría salido a la red creyendo que no.
    Pasó.
    """
    if consultar is None:
        consultar = ultima_publicada
    if fijadas is None:
        fijadas = {}

    fuera_de_rango, candado_atrasado = [], []
    sin_comparar, sin_respuesta = [], []

    for nombre, rango in sorted(declaradas(manifiesto).items()):
        if not nombre.startswith(PROPIAS):
            continue
        try:
            ultima = consultar(nombre)
        except Exception as error:
            sin_respuesta.append((nombre, str(error)))
            continue

        fijada = fijadas.get(nombre)

        # Antes que nada: si no se pueden ordenar, no se ordenan. Las dos
        # comprobaciones de abajo se apoyan en comparar los tres números.
        if es_preliberacion(ultima) or es_preliberacion(fijada):
            sin_comparar.append((nombre, fijada or rango, ultima))
            continue

        if not alcanza(rango, ultima):
            fuera_de_rango.append((nombre, rango, ultima))
            continue

        # Sin candado no hay nada que comparar. No es lo mismo que estar al
        # día, pero tampoco es un atraso: lo dice `main` aparte, para no
        # afirmar que se comprobó algo que no se comprobó.
        if fijada and partes(fijada) < partes(ultima):
            candado_atrasado.append((nombre, fijada, ultima))

    return fuera_de_rango, candado_atrasado, sin_comparar, sin_respuesta


def main(argv=None):
    opciones = argparse.ArgumentParser(description=__doc__)
    opciones.add_argument("--manifiesto", default="package.json")
    opciones.add_argument("--candado", default="bun.lock")
    opciones.add_argument(
        "--cortar",
        action="store_true",
        help="Salir con error en vez de sólo avisar. No alcanza al candado.",
    )
    opciones.add_argument(
        "--el-candado-corta",
        action="store_true",
        help=(
            "Que un candado atrasado también corte. Se pide aparte porque "
            "encenderlo pone en rojo a repositorios que hoy pasan."
        ),
    )
    elegido = opciones.parse_args(argv)

    try:
        with open(elegido.manifiesto, encoding="utf-8") as archivo:
            manifiesto = json.load(archivo)
    except FileNotFoundError:
        print(f"No hay {elegido.manifiesto}; no hay nada que comprobar.")
        return 0

    try:
        with open(elegido.candado, encoding="utf-8") as archivo:
            fijadas = resueltas(archivo.read())
    except FileNotFoundError:
        fijadas = None

    fuera_de_rango, candado_atrasado, sin_comparar, sin_respuesta = revisar(
        manifiesto, fijadas=fijadas, consultar=None
    )

    for nombre, motivo in sin_respuesta:
        # El registro caído no puede cortar la corrida: no dice nada sobre el
        # código del PR.
        print(f"::warning::No se pudo consultar {nombre} ({motivo}); no se comprobó.")

    for nombre, tenemos, ultima in sin_comparar:
        print(
            f"::warning::{nombre} está en {tenemos} y la última publicada es "
            f"{ultima}. Hay una preliberación de por medio y este guardia no "
            f"sabe ordenarlas: no se comprobó."
        )

    for nombre, rango, ultima in fuera_de_rango:
        print(
            f"::warning::{nombre} declara {rango} y la última publicada es "
            f"{ultima}. El rango no puede llegar: hay que subirlo a mano en "
            f"{elegido.manifiesto}."
        )

    for nombre, fijada, ultima in candado_atrasado:
        # El rango está bien y aun así se empaqueta lo viejo. Decirlo con el
        # comando puesto, porque el arreglo no es el mismo que el de arriba y
        # el aviso anterior mandaba a editar el manifiesto — que acá no hay
        # nada que editar.
        print(
            f"::warning::{nombre} se empaqueta en {fijada} y la última "
            f"publicada es {ultima}. El rango sí alcanza: lo que quedó atrás "
            f"es {elegido.candado}. Se arregla con `bun update {nombre}`."
        )

    if fijadas is None:
        # No es lo mismo que estar al día. Sin esto, un repositorio sin candado
        # leería «las bibliotecas propias están al día» habiendo comprobado la
        # mitad, que es la forma de mentir que este guardia vino a evitar.
        print(
            f"::warning::No hay {elegido.candado}; no se comprobó qué versión "
            f"se empaqueta de verdad."
        )

    if not fuera_de_rango and not candado_atrasado:
        if sin_respuesta or sin_comparar or fijadas is None:
            # Decir «están al día» después de avisar que algo no se pudo
            # comprobar es afirmar algo que no se comprobó, y las dos líneas
            # juntas se contradicen: se lee la segunda y se olvida la primera.
            print("Ninguna de las que se pudieron comprobar está atrasada.")
        else:
            print("Las bibliotecas propias están al día.")
        return 0

    corta = (fuera_de_rango and elegido.cortar) or (
        candado_atrasado and elegido.el_candado_corta
    )
    return 1 if corta else 0


if __name__ == "__main__":
    sys.exit(main())
