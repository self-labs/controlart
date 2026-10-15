"""Toda chave de traducao usada pelas luzes existe nos tres arquivos de texto."""

from __future__ import annotations

import json
import unittest

from ha_falso import PACOTE, light

ARQUIVOS = ["strings.json", "translations/en.json", "translations/pt-BR.json"]


class Traducoes(unittest.TestCase):
    def test_luzes_tem_nome_em_todos_os_idiomas(self):
        chaves = {light.Saida._attr_translation_key, light.CanalDimmer._attr_translation_key}
        for arquivo in ARQUIVOS:
            textos = json.loads((PACOTE / arquivo).read_text(encoding="utf-8"))
            for chave in chaves:
                with self.subTest(arquivo=arquivo, chave=chave):
                    self.assertIn("{numero}", textos["entity"]["light"][chave]["name"])

    def test_en_igual_ao_strings(self):
        strings = json.loads((PACOTE / "strings.json").read_text(encoding="utf-8"))
        en = json.loads((PACOTE / "translations/en.json").read_text(encoding="utf-8"))
        self.assertEqual(strings, en)


if __name__ == "__main__":
    unittest.main()
