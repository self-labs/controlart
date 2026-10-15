"""Firmware e MAC no card "Informacoes do dispositivo" do Home Assistant.

O MAC ja vem no cadastro (os tres ultimos bytes, que e tudo o que o modulo
informa) e entra no dispositivo desde a criacao. O firmware so chega depois
da conexao, entao atualiza o dispositivo ja registrado.
"""

from __future__ import annotations

import sys
import unittest

from ha_falso import light, protocolo, registro, sinais

MAC = "4E-50-D2"


def rele():
    sinais.clear()
    return protocolo.ModuloConexao(
        None, {"mac": MAC, "host": "192.168.68.21", "port": 4998, "name": "Hubb M1"}
    )


class Firmware(unittest.TestCase):
    def test_numero_vira_versao_com_ponto(self):
        mod = rele()
        mod._trata_linha("3027")
        self.assertEqual(mod.versao_firmware, "3.027")

    def test_dimmer(self):
        mod = rele()
        mod._trata_linha("1021")
        self.assertEqual(mod.versao_firmware, "1.021")

    def test_formato_do_driver_hubitat(self):
        mod = rele()
        mod._trata_linha("VERSION 3.022")
        self.assertEqual(mod.versao_firmware, "3.022")

    def test_sem_resposta_fica_vazio(self):
        self.assertIsNone(rele().versao_firmware)

    def test_avisa_quando_chega(self):
        mod = rele()
        mod._trata_linha("3027")
        self.assertIn(f"controlart_identidade_{MAC}", sinais)

    def test_nao_avisa_de_novo_se_nao_mudou(self):
        mod = rele()
        mod._trata_linha("3027")
        sinais.clear()
        mod._trata_linha("3027")
        self.assertNotIn(f"controlart_identidade_{MAC}", sinais)


class Mac(unittest.TestCase):
    def test_dispositivo_tem_o_mac(self):
        info = light.Saida(rele(), 1)._attr_device_info
        self.assertEqual(info["connections"], {("mac", MAC)})


class RegistroFalso:
    def __init__(self, sw_version=None):
        self.dispositivo = type("Dispositivo", (), {"id": "d1", "sw_version": sw_version})()
        self.atualizacoes: list[dict] = []
        self.procurado = None

    def async_get_device(self, identifiers=None, connections=None):
        self.procurado = identifiers
        return self.dispositivo

    def async_update_device(self, device_id, **mudancas):
        self.atualizacoes.append({"id": device_id, **mudancas})


class AtualizaDispositivo(unittest.TestCase):
    def setUp(self):
        self.dr = sys.modules["homeassistant.helpers.device_registry"]

    def tearDown(self):
        self.dr.async_get = None

    def test_grava_o_firmware(self):
        falso = RegistroFalso()
        self.dr.async_get = lambda hass: falso
        mod = rele()
        mod._trata_linha("3027")
        registro.atualiza_dispositivo(None, mod)
        self.assertEqual(falso.procurado, {("controlart", MAC)})
        self.assertEqual(falso.atualizacoes, [{"id": "d1", "sw_version": "3.027"}])

    def test_firmware_igual_nao_regrava(self):
        falso = RegistroFalso(sw_version="3.027")
        self.dr.async_get = lambda hass: falso
        mod = rele()
        mod._trata_linha("3027")
        registro.atualiza_dispositivo(None, mod)
        self.assertEqual(falso.atualizacoes, [])

    def test_sem_firmware_nao_mexe(self):
        falso = RegistroFalso(sw_version="3.027")
        self.dr.async_get = lambda hass: falso
        registro.atualiza_dispositivo(None, rele())
        self.assertEqual(falso.atualizacoes, [])


if __name__ == "__main__":
    unittest.main()
