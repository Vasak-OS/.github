#!/usr/bin/env python3
"""Las pruebas del guardia. Sin dependencias: `python3 -m unittest` y listo.

Importan más de lo que parece porque este guardia corre en treinta repositorios
y lo único que produce es un aviso: si se equivoca hacia el lado permisivo, no
avisa y nadie se entera — que es exactamente el fallo que vino a evitar.
"""

import unittest

from bibliotecas_al_dia import alcanza, declaradas, main, revisar


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
        atrasadas, _ = revisar(manifiesto, consultar=lambda n: "9.9.9")

        self.assertEqual(
            [n for n, _, _ in atrasadas], ["@vasakgroup/vue-libvasak"]
        )

    def test_lo_que_esta_al_dia_no_aparece(self):
        manifiesto = {"dependencies": {"@vasakgroup/x": "^1.0.0"}}
        atrasadas, sin_respuesta = revisar(manifiesto, consultar=lambda n: "1.4.0")

        self.assertEqual(atrasadas, [])
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
        atrasadas, sin_respuesta = revisar(manifiesto, consultar=se_cae)

        self.assertEqual(atrasadas, [])
        self.assertEqual([n for n, _ in sin_respuesta], ["@vasakgroup/x"])


class ComoTermina(unittest.TestCase):
    def test_sin_manifiesto_no_es_un_error(self):
        # Los repositorios que no son aplicaciones no tienen `package.json`, y
        # el guardia no tiene nada que decir sobre ellos.
        self.assertEqual(main(["--manifiesto", "no-existe.json", "--cortar"]), 0)


if __name__ == "__main__":
    unittest.main()
