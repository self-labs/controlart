"""Endereco IP do modulo, visivel no dispositivo como sensor de diagnostico."""

from __future__ import annotations

import importlib
import json
import unittest

from ha_falso import PACOTE, protocolo, registro

sensor = importlib.import_module("controlart.sensor")

MAC = "AA-BB-CC"


def modulo():
    return protocolo.ModuloConexao(
        None, {"mac": MAC, "host": "192.168.68.21", "port": 4998, "name": "Hubb M1"}
    )


class EnderecoIP(unittest.TestCase):
    def test_mostra_o_ip_cadastrado(self):
        self.assertEqual(sensor.EnderecoIP(modulo()).native_value, "192.168.68.21")

    def test_continua_visivel_com_o_modulo_fora(self):
        mod = modulo()
        mod.conectado = False
        self.assertTrue(sensor.EnderecoIP(mod).available)

    def test_e_diagnostico(self):
        self.assertEqual(sensor.EnderecoIP(modulo())._attr_entity_category, "diagnostic")

    def test_registro_nao_apaga_o_sensor(self):
        alvo = registro.esperado([{"mac": MAC}])
        self.assertIn(("sensor", f"controlart_{MAC}_ip"), alvo)

    def test_nome_em_todos_os_idiomas(self):
        chave = sensor.EnderecoIP._attr_translation_key
        for arquivo in ["strings.json", "translations/en.json", "translations/pt-BR.json"]:
            with self.subTest(arquivo=arquivo):
                textos = json.loads((PACOTE / arquivo).read_text(encoding="utf-8"))
                self.assertTrue(textos["entity"]["sensor"][chave]["name"])


if __name__ == "__main__":
    unittest.main()
