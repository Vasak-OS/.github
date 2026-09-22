#!/usr/bin/env python3
"""Las pruebas del guardia. Sin dependencias: `python3 -m unittest` y listo.

Importan más de lo que parece porque este guardia corre en treinta repositorios
y lo único que produce es un aviso: si se equivoca hacia el lado permisivo, no
avisa y nadie se entera — que es exactamente el fallo que vino a evitar.
"""

import os
import unittest

from bibliotecas_al_dia import (
    atrasadas_a_proposito,
    alcanza,
    declaradas,
    es_preliberacion,
    main,
    resueltas,
    revisar,
)


def candado(fijadas):
    """Un `bun.lock` de mentira con esas versiones, en el formato de verdad.

    Con las comas finales incluidas, que son la razón de que el candado se lea
    con una expresión regular y no con `json.load`.
    """
    lineas = [
        f'    "{nombre}": ["{nombre}@{version}", "", {{ }}, "sha512-xx"],'
        for nombre, version in fijadas.items()
    ]
    return '{\n  "lockfileVersion": 1,\n  "packages": {\n' + "\n".join(lineas) + "\n  }\n}\n"


class ElAcentoEnUnaVersionCero(unittest.TestCase):
    def test_el_acento_en_cero_fija_la_minor(self):
        # El caso que partió el taller dos veces. `^0.7.2` acepta cualquier
        # 0.7.x y ninguna 0.8.x, aunque el acento en una versión 1.x o mayor
        # signifique lo contrario.
        self.assertTrue(alcanza("^0.7.2", "0.7.9"))
        self.assertFalse(alcanza("^0.7.2", "0.8.0"))
        self.assertFalse(alcanza("^0.7.2", "0.19.0"))

    def test_el_acento_en_cero_cero_fija_el_parche(self):
        # `^0.0.6` es todavía más estrecho: sólo esa.
        self.assertTrue(alcanza("^0.0.6", "0.0.6"))
        self.assertFalse(alcanza("^0.0.6", "0.0.7"))
        self.assertFalse(alcanza("^0.0.6", "1.0.0"))

    def test_el_acento_en_uno_o_mas_fija_la_mayor(self):
        # Acá el acento hace lo que todo el mundo cree que hace, y por eso ir a
        # 1.0 sería el arreglo de raíz.
        self.assertTrue(alcanza("^1.2.3", "1.9.9"))
        self.assertFalse(alcanza("^1.2.3", "2.0.0"))


class ElPisoDelRango(unittest.TestCase):
    """Un rango tiene dos extremos, y el de abajo es el que se olvida.

    Lo encontró la revisión de CodeRabbit: la primera versión sólo miraba el
    techo, así que `^0.7.2` daba por alcanzable la 0.7.1. Pasa cuando lo
    publicado es **más viejo** que lo declarado —una versión que se dio de
    baja, un número que se subió antes de publicarlo— y ahí el guardia se
    callaba justo en un estado que alguien debería mirar.
    """

    def test_lo_publicado_mas_viejo_que_lo_declarado_no_alcanza(self):
        self.assertFalse(alcanza("^0.7.2", "0.7.1"))
        self.assertFalse(alcanza("~2.7.3", "2.7.1"))
        self.assertFalse(alcanza("^1.2.3", "1.0.0"))

    def test_lo_publicado_igual_a_lo_declarado_sí_alcanza(self):
        # El borde de abajo entra: `^0.7.2` acepta exactamente la 0.7.2.
        self.assertTrue(alcanza("^0.7.2", "0.7.2"))
        self.assertTrue(alcanza("~2.7.3", "2.7.3"))


class OtrasFormasDeRango(unittest.TestCase):
    def test_la_virgulilla_fija_la_minor_siempre(self):
        self.assertTrue(alcanza("~2.7.3", "2.7.9"))
        self.assertFalse(alcanza("~2.7.3", "2.8.0"))

    def test_una_version_exacta_no_llega_a_ninguna_otra(self):
        self.assertTrue(alcanza("1.2.3", "1.2.3"))
        self.assertFalse(alcanza("1.2.3", "1.2.4"))

    def test_lo_que_no_es_un_rango_de_version_se_deja_pasar(self):
        # `workspace:*`, un `git://`, un `*`. No es algo que este guardia pueda
        # juzgar, y tratarlo como atrasado sería un aviso falso en cada corrida
        # — que es la forma de que dejen de mirarse los avisos.
        for raro in ("workspace:*", "*", "git+https://x/y.git", "latest", ""):
            self.assertTrue(alcanza(raro, "9.9.9"), raro)


class QueMira(unittest.TestCase):
    def test_junta_las_dos_secciones(self):
        manifiesto = {
            "dependencies": {"a": "^1.0.0"},
            "devDependencies": {"b": "^2.0.0"},
        }
        self.assertEqual(declaradas(manifiesto), {"a": "^1.0.0", "b": "^2.0.0"})

    def test_solo_avisa_por_las_propias(self):
        # Una de terceros atrasada suele ser una decisión —subir una mayor
        # rompe cosas—; quedarse atrás en la nuestra no lo decide nadie.
        manifiesto = {
            "dependencies": {
                "@vasakgroup/vue-libvasak": "^0.7.2",
                "vue": "^3.0.0",
            }
        }
        fuera, *_ = revisar(manifiesto, consultar=lambda n: "9.9.9")

        self.assertEqual([n for n, _, _ in fuera], ["@vasakgroup/vue-libvasak"])

    def test_lo_que_esta_al_dia_no_aparece(self):
        manifiesto = {"dependencies": {"@vasakgroup/x": "^1.0.0"}}
        fuera, candado, _, sin_respuesta, _ = revisar(
            manifiesto,
            fijadas={"@vasakgroup/x": "1.4.0"},
            consultar=lambda n: "1.4.0",
        )

        self.assertEqual(fuera, [])
        self.assertEqual(candado, [])
        self.assertEqual(sin_respuesta, [])


class CuandoElRegistroNoContesta(unittest.TestCase):
    def test_no_se_confunde_con_estar_atrasada(self):
        # El registro caído no dice nada sobre el código del PR. Contarlo como
        # atrasada sería cortar corridas por un problema de red; contarlo como
        # al día sería decir que se comprobó algo que no se comprobó. Va en su
        # propia lista, y se avisa.
        def se_cae(nombre):
            raise OSError("sin red")

        manifiesto = {"dependencies": {"@vasakgroup/x": "^0.1.0"}}
        fuera, candado, _, sin_respuesta, _ = revisar(manifiesto, consultar=se_cae)

        self.assertEqual(fuera, [])
        self.assertEqual(candado, [])
        self.assertEqual([n for n, _ in sin_respuesta], ["@vasakgroup/x"])


class ComoTermina(unittest.TestCase):
    @staticmethod
    def se_cae(nombre):
        raise OSError("sin red")

    def correr(self, manifiesto, consultar, candado=None, banderas=()):
        """Corre `main` sobre un manifiesto de mentira y devuelve lo que imprimió.

        `candado` es el **texto** de un `bun.lock`, no un diccionario: lo que
        hay que probar es que se sepa leer ese formato, y pasarlo ya parseado
        saltearía justamente la parte que se puede equivocar.
        """
        import contextlib
        import io
        import json
        import tempfile

        import bibliotecas_al_dia

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as archivo:
            json.dump(manifiesto, archivo)
            ruta = archivo.name

        ruta_candado = "no-existe.lock"
        if candado is not None:
            with tempfile.NamedTemporaryFile(
                "w", suffix=".lock", delete=False
            ) as archivo:
                archivo.write(candado)
                ruta_candado = archivo.name

        original = bibliotecas_al_dia.ultima_publicada
        bibliotecas_al_dia.ultima_publicada = consultar
        salida = io.StringIO()
        try:
            with contextlib.redirect_stdout(salida):
                self.salida_de_main = bibliotecas_al_dia.main(
                    ["--manifiesto", ruta, "--candado", ruta_candado, *banderas]
                )
        finally:
            bibliotecas_al_dia.ultima_publicada = original
            os.unlink(ruta)
            if candado is not None:
                os.unlink(ruta_candado)

        return salida.getvalue()

    def test_no_dice_que_estan_al_dia_si_alguna_no_se_pudo_consultar(self):
        # Avisar que no se pudo comprobar una y después decir «están al día»
        # es afirmar algo que no se comprobó. Y las dos líneas juntas se
        # contradicen: se lee la última y se olvida la primera.
        salida = self.correr(
            {"dependencies": {"@vasakgroup/x": "^1.0.0"}},
            consultar=self.se_cae,
        )

        self.assertIn("No se pudo consultar", salida)
        self.assertNotIn("están al día", salida)

    def test_dice_que_estan_al_dia_solo_cuando_las_vio_a_todas(self):
        salida = self.correr(
            {"dependencies": {"@vasakgroup/x": "^1.0.0"}},
            consultar=lambda nombre: "1.4.0",
            candado=candado({"@vasakgroup/x": "1.4.0"}),
        )

        self.assertIn("están al día", salida)

    def test_sin_candado_no_dice_que_estan_al_dia(self):
        # El rango alcanza, así que la mitad vieja del guardia habría dicho
        # «al día» sin haber mirado qué se empaqueta. Eso es la mentira que
        # dejó once repositorios atrás en verde.
        salida = self.correr(
            {"dependencies": {"@vasakgroup/x": "^1.0.0"}},
            consultar=lambda nombre: "1.4.0",
        )

        self.assertIn("no se comprobó qué versión se empaqueta", salida)
        self.assertNotIn("están al día", salida)

    def test_sin_manifiesto_no_es_un_error(self):
        # Los repositorios que no son aplicaciones no tienen `package.json`, y
        # el guardia no tiene nada que decir sobre ellos.
        self.assertEqual(main(["--manifiesto", "no-existe.json", "--cortar"]), 0)


class LoQueSeEmpaquetaDeVerdad(unittest.TestCase):
    """El candado, que es la mitad que faltaba.

    El rango dice qué se **podría** instalar; el candado, qué se instala. Un
    candado que ya satisface el rango no se mueve solo, así que las dos cosas
    se separan y nadie se entera: el 2026-09-22 había once repositorios
    atrasados con este guardia en verde.
    """

    def test_lee_la_version_fijada(self):
        fijadas = resueltas(candado({"@vasakgroup/vue-libvasak": "1.0.0"}))

        self.assertEqual(fijadas, {"@vasakgroup/vue-libvasak": "1.0.0"})

    def test_ignora_las_copias_anidadas(self):
        # Una clave con barra es otra copia del paquete, la que usa `vite` y no
        # la que usa la aplicación. Tomarla informaría una versión que no es la
        # que se empaqueta.
        texto = candado({"esbuild": "0.25.0"}).replace(
            '"esbuild":', '"vite/esbuild":', 1
        )

        self.assertEqual(resueltas(texto), {})

    def test_el_rango_alcanza_y_aun_asi_esta_atrasada(self):
        # El caso entero. `^1.0.0` admite la 1.4.0 y el candado dice 1.0.0.
        manifiesto = {"dependencies": {"@vasakgroup/x": "^1.0.0"}}
        fuera, atrasado, *_ = revisar(
            manifiesto,
            fijadas={"@vasakgroup/x": "1.0.0"},
            consultar=lambda n: "1.4.0",
        )

        self.assertEqual(fuera, [])
        self.assertEqual(atrasado, [("@vasakgroup/x", "1.0.0", "1.4.0")])

    def test_la_que_esta_fuera_de_rango_no_se_cuenta_dos_veces(self):
        # Es la misma biblioteca y el mismo arreglo. Avisar por las dos vías
        # manda a editar el manifiesto y a correr `bun update`, y sólo una de
        # las dos sirve.
        manifiesto = {"dependencies": {"@vasakgroup/x": "^0.19.0"}}
        fuera, atrasado, *_ = revisar(
            manifiesto,
            fijadas={"@vasakgroup/x": "0.19.0"},
            consultar=lambda n: "1.4.0",
        )

        self.assertEqual([n for n, _, _ in fuera], ["@vasakgroup/x"])
        self.assertEqual(atrasado, [])

    def test_el_candado_adelantado_no_es_un_atraso(self):
        # Pasa entre que se publica y que el registro lo marca como `latest`,
        # y también con una versión que se dio de baja.
        _, atrasado, *_ = revisar(
            {"dependencies": {"@vasakgroup/x": "^1.0.0"}},
            fijadas={"@vasakgroup/x": "1.5.0"},
            consultar=lambda n: "1.4.0",
        )

        self.assertEqual(atrasado, [])

    def test_de_terceros_no_se_mira_tampoco_acá(self):
        _, atrasado, *_ = revisar(
            {"dependencies": {"vue": "^3.0.0"}},
            fijadas={"vue": "3.0.0"},
            consultar=lambda n: "3.5.43",
        )

        self.assertEqual(atrasado, [])


class QueCortaYQueNo(unittest.TestCase):
    """Un candado atrasado avisa; cortar se pide aparte.

    Encenderlo junto con `--cortar` pondría en rojo, de una, a los once
    repositorios que hoy pasan: su próximo PR no se podría mergear hasta
    subirlos. Avisar primero y cortar después es lo mismo que se hizo con el
    rango cuando este guardia se estrenó.
    """

    def correr(self, manifiesto, fijadas, banderas):
        return ComoTermina.correr(
            self,
            manifiesto,
            consultar=lambda n: "1.4.0",
            candado=candado(fijadas),
            banderas=banderas,
        )

    def test_el_candado_atrasado_avisa_pero_no_corta(self):
        self.correr(
            {"dependencies": {"@vasakgroup/x": "^1.0.0"}},
            {"@vasakgroup/x": "1.0.0"},
            ["--cortar"],
        )

        self.assertEqual(self.salida_de_main, 0)

    def test_y_corta_cuando_se_pide(self):
        self.correr(
            {"dependencies": {"@vasakgroup/x": "^1.0.0"}},
            {"@vasakgroup/x": "1.0.0"},
            ["--cortar", "--el-candado-corta"],
        )

        self.assertEqual(self.salida_de_main, 1)

    def test_el_aviso_manda_a_bun_update_y_no_a_editar_el_manifiesto(self):
        # Son dos arreglos distintos y el aviso de antes mandaba a «subirlo a
        # mano», que acá no sirve: en el manifiesto no hay nada que corregir.
        salida = self.correr(
            {"dependencies": {"@vasakgroup/x": "^1.0.0"}},
            {"@vasakgroup/x": "1.0.0"},
            [],
        )

        self.assertIn("bun update @vasakgroup/x", salida)
        self.assertNotIn("hay que subirlo a mano", salida)


class CuandoHayUnaPreliberacion(unittest.TestCase):
    """Dos versiones que este guardia no sabe ordenar.

    `partes()` se queda con los tres números, así que la `1.4.0-beta.1` y la
    `1.4.0-beta.2` le salen iguales — y ahí la comparación del candado daría
    «al día» sin haber comparado nada. Lo marcó la revisión de CodeRabbit.

    Ordenarlas bien es implementar la precedencia de SemVer entera, y ninguno
    de los diez paquetes propios publicó una preliberación nunca: 81 versiones,
    cero con guion. Así que no se compara y **se dice**, que es lo que este
    guardia ya hace con el registro caído y con el candado que no está.
    """

    def test_reconoce_la_etiqueta(self):
        self.assertTrue(es_preliberacion("1.4.0-beta.1"))
        self.assertTrue(es_preliberacion("0.19.0-rc.1"))
        self.assertFalse(es_preliberacion("1.4.0"))
        self.assertFalse(es_preliberacion(""))
        self.assertFalse(es_preliberacion(None))

    def test_dos_preliberaciones_distintas_no_se_dan_por_iguales(self):
        # El caso exacto del hallazgo: sin esto, `partes()` las ve iguales y
        # el candado atrasado no aparece.
        _, atrasado, sin_comparar, *_ = revisar(
            {"dependencies": {"@vasakgroup/x": "^1.0.0"}},
            fijadas={"@vasakgroup/x": "1.4.0-beta.1"},
            consultar=lambda n: "1.4.0-beta.2",
        )

        self.assertEqual(atrasado, [])
        self.assertEqual(
            sin_comparar, [("@vasakgroup/x", "1.4.0-beta.1", "1.4.0-beta.2")]
        )

    def test_tampoco_se_juzga_el_rango_contra_una_preliberacion(self):
        # La misma ceguera estaba del otro lado: `alcanza('^0.19.0', ...)` se
        # apoya en los mismos tres números. Si no se pueden ordenar, no se
        # contesta ni que alcanza ni que no.
        fuera, _, sin_comparar, *_ = revisar(
            {"dependencies": {"@vasakgroup/x": "^0.19.0"}},
            fijadas={"@vasakgroup/x": "0.19.0"},
            consultar=lambda n: "1.0.0-rc.1",
        )

        self.assertEqual(fuera, [])
        self.assertEqual([n for n, _, _ in sin_comparar], ["@vasakgroup/x"])

    def test_no_dice_que_estan_al_dia_si_no_pudo_comparar(self):
        salida = ComoTermina.correr(
            self,
            {"dependencies": {"@vasakgroup/x": "^1.0.0"}},
            consultar=lambda n: "1.4.0-beta.2",
            candado=candado({"@vasakgroup/x": "1.4.0-beta.1"}),
        )

        self.assertIn("no sabe ordenarlas", salida)
        self.assertNotIn("están al día", salida)

    def test_y_una_version_normal_se_sigue_comparando(self):
        # El guardia no se vuelve mudo por las dudas: sin guion, compara.
        _, atrasado, sin_comparar, *_ = revisar(
            {"dependencies": {"@vasakgroup/x": "^1.0.0"}},
            fijadas={"@vasakgroup/x": "1.0.0"},
            consultar=lambda n: "1.4.0",
        )

        self.assertEqual(sin_comparar, [])
        self.assertEqual(atrasado, [("@vasakgroup/x", "1.0.0", "1.4.0")])


class UnAtrasoDeclaradoConMotivo(unittest.TestCase):
    """Quedarse atrás a propósito, dicho y no escondido.

    La premisa del guardia —«quedarse atrás en una biblioteca propia no lo
    decide nadie»— tenía un hueco, y apareció el 2026-09-22: la 2.7.0 de
    `plugin-config-manager` declara `pinia: ^4.0.0` y `vasak-file-manager` está
    en pinia 3, así que subir el rango arrastraba un salto mayor ajeno al
    cambio. Sin forma de declararlo había que apagar el guardia para el
    repositorio entero —y perder la vigilancia sobre `vue-libvasak`, que es para
    lo que existe—.
    """

    MANIFIESTO = {
        "dependencies": {"@vasakgroup/x": "~1.0.0"},
        "vasak": {"bibliotecasAtrasadas": {"@vasakgroup/x": "la 1.4 pide pinia 4"}},
    }

    def test_un_rango_que_no_alcanza_deja_de_cortar_si_esta_declarado(self):
        fuera, _, _, _, declaradas = revisar(
            self.MANIFIESTO, consultar=lambda n: "1.4.0"
        )

        self.assertEqual(fuera, [], "declarado, no cuenta como atraso a arreglar")
        self.assertEqual(
            declaradas,
            [("@vasakgroup/x", "~1.0.0", "1.4.0", "la 1.4 pide pinia 4")],
        )

    def test_pero_se_sigue_avisando_con_el_motivo_puesto(self):
        # No se silencia: se deja de cortar. Una excepción que no se ve es una
        # que nadie va a revisar el día que el motivo deje de valer.
        salida = ComoTermina.correr(
            self, self.MANIFIESTO, consultar=lambda n: "1.4.0", banderas=["--cortar"]
        )

        self.assertIn("la 1.4 pide pinia 4", salida)
        self.assertIn("vasak.bibliotecasAtrasadas", salida)
        self.assertEqual(self.salida_de_main, 0)

    def test_y_no_dice_que_estan_al_dia(self):
        # Porque no lo están. Decirlo sería la forma de mentir que este guardia
        # vino a evitar, sólo que con permiso.
        salida = ComoTermina.correr(
            self, self.MANIFIESTO, consultar=lambda n: "1.4.0", banderas=["--cortar"]
        )

        self.assertNotIn("están al día", salida)

    def test_una_declaracion_sin_motivo_no_vale(self):
        # Lo que convierte una versión vieja en una decisión es la explicación.
        # Sin ella esto sería un interruptor para apagar el guardia de a una
        # biblioteca por vez, que es peor que apagarlo entero porque no se ve.
        for vacio in ("", "   ", None, 42):
            with self.subTest(motivo=vacio):
                manifiesto = {
                    "dependencies": {"@vasakgroup/x": "~1.0.0"},
                    "vasak": {"bibliotecasAtrasadas": {"@vasakgroup/x": vacio}},
                }
                fuera, _, _, _, declaradas = revisar(
                    manifiesto, consultar=lambda n: "1.4.0"
                )

                self.assertEqual(declaradas, [])
                self.assertEqual(len(fuera), 1, "sigue contando como atraso")

    def test_declarar_una_no_tapa_a_las_demas(self):
        # El error que haría inútil todo esto: una excepción que se lleve
        # puestas las otras bibliotecas del mismo repositorio.
        manifiesto = {
            "dependencies": {
                "@vasakgroup/x": "~1.0.0",
                "@vasakgroup/vue-libvasak": "^0.7.0",
            },
            "vasak": {"bibliotecasAtrasadas": {"@vasakgroup/x": "un motivo"}},
        }
        fuera, _, _, _, declaradas = revisar(manifiesto, consultar=lambda n: "1.4.0")

        self.assertEqual([n for n, *_ in declaradas], ["@vasakgroup/x"])
        self.assertEqual(
            [n for n, *_ in fuera],
            ["@vasakgroup/vue-libvasak"],
            "la otra sigue cortando",
        )

    def test_tambien_cubre_el_candado_atrasado(self):
        # El otro atraso: el rango alcanza y el candado no se movió. Si la
        # excepción no lo cubriera, declarar el motivo arreglaría la mitad y el
        # repositorio seguiría en rojo por la otra, sin nada que hacer.
        manifiesto = {
            "dependencies": {"@vasakgroup/x": "^1.0.0"},
            "vasak": {"bibliotecasAtrasadas": {"@vasakgroup/x": "un motivo"}},
        }
        _, atrasado, _, _, declaradas = revisar(
            manifiesto, fijadas={"@vasakgroup/x": "1.0.0"}, consultar=lambda n: "1.4.0"
        )

        self.assertEqual(atrasado, [])
        self.assertEqual(len(declaradas), 1)

    def test_sin_la_seccion_no_pasa_nada(self):
        # Lo normal: casi ningún repositorio la va a tener.
        self.assertEqual(atrasadas_a_proposito({}), {})
        self.assertEqual(atrasadas_a_proposito({"vasak": {}}), {})
        self.assertEqual(
            atrasadas_a_proposito({"vasak": {"bibliotecasAtrasadas": "no es un objeto"}}),
            {},
        )


if __name__ == "__main__":
    unittest.main()
