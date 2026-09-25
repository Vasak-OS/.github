"""El FUNDING.yml de la organización.

GitHub lo valida al mostrar el botón «Sponsor» y, si algo no le cierra, el
botón simplemente no aparece en ningún repositorio: no hay error ni aviso.
Estas pruebas son las reglas que se pueden romper editándolo a mano.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FUNDING = ROOT / ".github" / "FUNDING.yml"

# Las plataformas que GitHub reconoce por nombre, más `custom`.
KNOWN_KEYS = {
    "github", "patreon", "open_collective", "ko_fi", "tidelift",
    "community_bridge", "liberapay", "issuehunt", "lfx_crowdfunding",
    "polar", "buy_me_a_coffee", "thanks_dev", "custom",
}


def read_funding():
    """Lee el YAML plano que usa este archivo, sin depender de PyYAML."""
    keys, custom, current = {}, [], None
    for line in FUNDING.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if match:
            current = match.group(1)
            keys[current] = match.group(2).strip()
            continue
        match = re.match(r"^\s+-\s+(\S+)\s*$", line)
        if match and current == "custom":
            custom.append(match.group(1))
            continue
        raise AssertionError(f"línea que no se entiende: {line!r}")
    return keys, custom


class FundingTest(unittest.TestCase):
    def test_only_keys_github_knows(self):
        """Sólo claves que GitHub reconoce."""
        keys, _ = read_funding()
        self.assertTrue(keys)
        self.assertLessEqual(set(keys), KNOWN_KEYS)

    def test_custom_has_at_most_four_https_links(self):
        """`custom` lleva a lo sumo cuatro enlaces, todos HTTPS y sin repetir."""
        _, custom = read_funding()
        self.assertGreater(len(custom), 0)
        self.assertLessEqual(len(custom), 4)
        for url in custom:
            self.assertTrue(url.startswith("https://"), url)
        self.assertEqual(len(set(custom)), len(custom))

    def test_links_to_donate_page(self):
        """Lleva a la página de donaciones.

        Lemon y las direcciones cripto sólo están ahí: sin este enlace, el
        botón ofrecería menos medios que el sitio.
        """
        _, custom = read_funding()
        self.assertIn("https://os.vasak.net.ar/donate/", custom)

    def test_ko_fi_is_a_username_not_a_url(self):
        """Ko-fi va como usuario: GitHub arma la URL y una entera rompe el botón."""
        keys, _ = read_funding()
        self.assertRegex(keys["ko_fi"], r"^[A-Za-z0-9_]+$")


if __name__ == "__main__":
    unittest.main()
