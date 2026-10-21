"""Firmware e MAC no card "Informacoes do dispositivo" do Home Assistant.

O cadastro guarda os tres ultimos bytes do MAC, que e tudo o que o modulo
informa; o card mostra o MAC inteiro, com o prefixo fixo 00-60-37 (ou o que
a descoberta viu). O firmware so chega depois da conexao, entao atualiza o
dispositivo ja registrado, e o MAC curto dos cadastros antigos sai junto.
"""

from __future__ import annotations

import sys
import unittest

from ha_falso import HomeAssistantError, light, protocolo, registro, sinais

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
    def test_card_mostra_o_mac_inteiro(self):
        info = light.Saida(rele(), 1)._attr_device_info
        self.assertEqual(info["connections"], {("mac", f"00-60-37-{MAC}")})

    def test_identificador_segue_o_mac_curto(self):
        info = light.Saida(rele(), 1)._attr_device_info
        self.assertEqual(info["identifiers"], {("controlart", MAC)})

    def test_vale_o_mac_que_a_descoberta_viu(self):
        mod = protocolo.ModuloConexao(None, {
            "mac": "AA-BB-CC", "full_mac": "02-11-22-AA-BB-CC",
            "host": "10.0.0.5", "port": 4998, "name": "M",
        })
        self.assertEqual(mod.mac_completo, "02-11-22-AA-BB-CC")

    def test_mac_como_o_dhcp_do_ha_entrega(self):
        self.assertEqual(protocolo.mac_da_rede("006037aabbcc"), "00-60-37-AA-BB-CC")
        self.assertEqual(protocolo.mac_da_rede("00:60:37:aa:bb:cc"), "00-60-37-AA-BB-CC")


INTEIRO = {("mac", "00:60:37:4e:50:d2")}   # como o registro do HA guarda


def dispositivo(ident, sw_version=None, connections=INTEIRO):
    return type("Dispositivo", (), {
        "id": ident[1], "identifiers": {ident}, "sw_version": sw_version,
        "connections": connections,
    })()


class RegistroFalso:
    """So o que atualiza_dispositivo usa. Sem async_get_device: desde o HA
    2026.10 ele avisa que esta obsoleto, e o substituto nao existe nas versoes
    antigas que o hacs.json ainda aceita."""

    def __init__(self, *dispositivos):
        self.dispositivos = list(dispositivos)
        self.atualizacoes: list[dict] = []

    def async_update_device(self, device_id, **mudancas):
        self.atualizacoes.append({"id": device_id, **mudancas})


class AtualizaDispositivo(unittest.TestCase):
    def setUp(self):
        self.dr = sys.modules["homeassistant.helpers.device_registry"]
        self.pedido_entry = None

    def tearDown(self):
        self.dr.async_get = None
        self.dr.async_entries_for_config_entry = None

    def usa(self, falso):
        def entries(registro_, entry_id):
            self.pedido_entry = entry_id
            return registro_.dispositivos

        self.dr.async_get = lambda hass: falso
        self.dr.async_entries_for_config_entry = entries

    def test_grava_o_firmware_so_no_dispositivo_do_modulo(self):
        falso = RegistroFalso(dispositivo(("controlart", "74-14-6E")), dispositivo(("controlart", MAC)))
        self.usa(falso)
        mod = rele()
        mod._trata_linha("3027")
        registro.atualiza_dispositivo(None, "entrada1", mod)
        self.assertEqual(self.pedido_entry, "entrada1")
        self.assertEqual(falso.atualizacoes, [{"id": MAC, "sw_version": "3.027"}])

    def test_firmware_igual_nao_regrava(self):
        falso = RegistroFalso(dispositivo(("controlart", MAC), sw_version="3.027"))
        self.usa(falso)
        mod = rele()
        mod._trata_linha("3027")
        registro.atualiza_dispositivo(None, "entrada1", mod)
        self.assertEqual(falso.atualizacoes, [])

    def test_sem_firmware_nao_mexe(self):
        falso = RegistroFalso(dispositivo(("controlart", MAC), sw_version="3.027"))
        self.usa(falso)
        registro.atualiza_dispositivo(None, "entrada1", rele())
        self.assertEqual(falso.atualizacoes, [])

    def test_cadastro_antigo_troca_o_mac_curto_pelo_inteiro(self):
        # ate a 2026.10.3 a conexao era o MAC curto; o registro soma conexoes
        antigo = {("mac", MAC), ("mac", "00:60:37:4e:50:d2")}
        falso = RegistroFalso(dispositivo(("controlart", MAC), sw_version="3.027", connections=antigo))
        self.usa(falso)
        registro.atualiza_dispositivo(None, "entrada1", rele())
        self.assertEqual(falso.atualizacoes, [{"id": MAC, "new_connections": INTEIRO}])

    def test_mac_de_outro_dispositivo_nao_impede_o_firmware(self):
        class RegistroComColisao(RegistroFalso):
            def async_update_device(self, device_id, **mudancas):
                if "new_connections" in mudancas:
                    raise HomeAssistantError("o MAC ja e de outro dispositivo")
                super().async_update_device(device_id, **mudancas)

        falso = RegistroComColisao(dispositivo(("controlart", MAC), connections={("mac", MAC)}))
        self.usa(falso)
        mod = rele()
        mod._trata_linha("3027")
        with self.assertLogs("controlart.registro", "WARNING"):
            registro.atualiza_dispositivo(None, "entrada1", mod)
        self.assertEqual(falso.atualizacoes, [{"id": MAC, "sw_version": "3.027"}])


if __name__ == "__main__":
    unittest.main()
