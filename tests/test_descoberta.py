"""Descoberta pela rede: o HA ve um aparelho com MAC 00:60:37 e chama o fluxo.

Modulo novo vira card (o primeiro cria a entrada, os seguintes entram nela);
modulo ja cadastrado so tem o IP atualizado; aparelho que nao responde como
ControlArt, ou responde com outro MAC, e descartado sem card.
"""

from __future__ import annotations

import unittest

from ha_falso import Abortado, config_flow, const, protocolo

RELE = protocolo.Identidade("AA-BB-CC", const.TIPO_RELE, 10)


def visto(ip="192.168.1.50", mac="006037aabbcc"):
    return type("DhcpServiceInfo", (), {"ip": ip, "macaddress": mac, "hostname": ""})()


class Entrada:
    def __init__(self, *modulos):
        self.options = {const.CONF_MODULOS: list(modulos)}


class Entradas:
    """hass.config_entries: guarda o que o fluxo gravou."""

    def __init__(self):
        self.gravado: list[tuple[Entrada, dict]] = []

    def async_update_entry(self, entrada, options):
        self.gravado.append((entrada, options))
        entrada.options = options


def cadastrado(mac="AA-BB-CC", host="192.168.1.50", **extra):
    return {"host": host, "port": 4998, "mac": mac, "name": "M1", "keypad_inputs": [], **extra}


class Descoberta(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._sonda = config_flow.sonda
        self.perguntados: list[tuple[str, int]] = []
        self.responde(RELE)

    def tearDown(self):
        config_flow.sonda = self._sonda

    def responde(self, identidade=None, erro=None):
        async def sonda(host, porta):
            self.perguntados.append((host, porta))
            if erro:
                raise erro
            return identidade

        config_flow.sonda = sonda

    def fluxo(self, *entradas, ignorados=()):
        fluxo = config_flow.ControlArtConfigFlow()
        fluxo.context = {}
        fluxo.entradas = list(entradas)
        fluxo.ignorados = set(ignorados)
        fluxo.hass = type("Hass", (), {"config_entries": Entradas()})()
        return fluxo

    async def test_modulo_novo_vira_card_com_o_mac_inteiro(self):
        fluxo = self.fluxo()
        passo = await fluxo.async_step_dhcp(visto())
        self.assertEqual(passo["type"], "form")
        self.assertEqual(passo["step_id"], "descoberto")
        self.assertEqual(passo["description_placeholders"],
                         {"mac": "00-60-37-AA-BB-CC", "host": "192.168.1.50"})
        self.assertEqual(fluxo.context["title_placeholders"], {"name": "ControlArt 00-60-37-AA-BB-CC"})
        self.assertEqual(fluxo.unique_id, "AA-BB-CC")
        self.assertEqual(self.perguntados, [("192.168.1.50", 4998)])

    async def test_primeiro_modulo_cria_a_entrada_unica(self):
        fluxo = self.fluxo()
        await fluxo.async_step_dhcp(visto())
        fim = await fluxo.async_step_descoberto({"name": "Sala", "keypad_inputs": ["3", "1"]})
        self.assertEqual(fim["type"], "create_entry")
        self.assertEqual(fluxo.unique_id, "controlart")
        self.assertEqual(fim["options"][const.CONF_MODULOS], [{
            "host": "192.168.1.50", "port": 4998, "mac": "AA-BB-CC",
            const.CONF_TIPO: const.TIPO_RELE, const.CONF_SAIDAS: 10, "name": "Sala",
            const.CONF_TECLAS: [1, 3], const.CONF_MAC_COMPLETO: "00-60-37-AA-BB-CC",
        }])

    async def test_segundo_modulo_entra_na_entrada_que_existe(self):
        entrada = Entrada(cadastrado(mac="11-22-33", host="192.168.1.40"))
        fluxo = self.fluxo(entrada)
        passo = await fluxo.async_step_dhcp(visto())
        self.assertEqual(passo["data_schema"], None)   # voluptuous falso
        fim = await fluxo.async_step_descoberto({"name": "", "keypad_inputs": []})
        self.assertEqual(fim, {"type": "abort", "reason": "modulo_adicionado"})
        macs = [m["mac"] for m in entrada.options[const.CONF_MODULOS]]
        self.assertEqual(macs, ["11-22-33", "AA-BB-CC"])
        self.assertEqual(entrada.options[const.CONF_MODULOS][1]["name"], "ControlArt AA-BB-CC")

    async def test_cadastrado_no_mesmo_ip_nao_mexe(self):
        entrada = Entrada(cadastrado(full_mac="00-60-37-AA-BB-CC"))
        fluxo = self.fluxo(entrada)
        fim = await fluxo.async_step_dhcp(visto())
        self.assertEqual(fim, {"type": "abort", "reason": "ja_cadastrado"})
        self.assertEqual(fluxo.hass.config_entries.gravado, [])
        self.assertEqual(self.perguntados, [])

    async def test_cadastrado_que_mudou_de_ip_e_corrigido(self):
        entrada = Entrada(cadastrado(host="192.168.1.50", port=5000))
        fluxo = self.fluxo(entrada)
        fim = await fluxo.async_step_dhcp(visto(ip="192.168.1.77"))
        self.assertEqual(fim["reason"], "ja_cadastrado")
        modulo = entrada.options[const.CONF_MODULOS][0]
        self.assertEqual(modulo["host"], "192.168.1.77")
        self.assertEqual(modulo["port"], 5000)            # porta mudada no mdConfig fica
        self.assertEqual(modulo[const.CONF_MAC_COMPLETO], "00-60-37-AA-BB-CC")
        self.assertEqual(self.perguntados, [])

    async def test_aparelho_que_nao_e_controlart_sai_sem_card(self):
        for erro in (protocolo.SemConexao(), protocolo.SemResposta()):
            with self.subTest(erro=type(erro).__name__):
                self.responde(erro=erro)
                fim = await self.fluxo().async_step_dhcp(visto())
                self.assertEqual(fim, {"type": "abort", "reason": "nao_e_controlart"})

    async def test_outro_modulo_respondendo_no_ip_sai_sem_card(self):
        self.responde(protocolo.Identidade("DD-EE-FF", const.TIPO_RELE, 10))
        fim = await self.fluxo().async_step_dhcp(visto())
        self.assertEqual(fim["reason"], "nao_e_controlart")

    async def test_modulo_ignorado_nao_volta(self):
        with self.assertRaises(Abortado):
            await self.fluxo(ignorados={"AA-BB-CC"}).async_step_dhcp(visto())
        self.assertEqual(self.perguntados, [])

    async def test_cadastrado_a_mao_enquanto_o_card_estava_aberto(self):
        entrada = Entrada()
        fluxo = self.fluxo(entrada)
        await fluxo.async_step_dhcp(visto())
        entrada.options = {const.CONF_MODULOS: [cadastrado()]}
        fim = await fluxo.async_step_descoberto({"name": "Sala", "keypad_inputs": []})
        self.assertEqual(fim, {"type": "abort", "reason": "ja_cadastrado"})

    async def test_editar_o_nome_nao_apaga_o_mac_visto(self):
        async def sonda_proibida(host, porta):
            raise AssertionError("nao precisa perguntar ao modulo")

        config_flow.sonda = sonda_proibida
        atual = cadastrado(full_mac="02-11-22-AA-BB-CC")
        modulo, erro = await config_flow._monta_modulo(
            {"host": "192.168.1.50", "port": 4998, "name": "Novo", "keypad_inputs": []}, [], atual
        )
        self.assertIsNone(erro)
        self.assertEqual(modulo[const.CONF_MAC_COMPLETO], "02-11-22-AA-BB-CC")


class Manifest(unittest.TestCase):
    def test_pede_ao_ha_os_aparelhos_com_o_prefixo(self):
        import json

        from ha_falso import PACOTE

        manifest = json.loads((PACOTE / "manifest.json").read_text(encoding="utf-8"))
        prefixo = const.PREFIXO_MAC.replace("-", "").lower()
        self.assertEqual(manifest["dhcp"], [{"macaddress": f"{prefixo}*"}])


if __name__ == "__main__":
    unittest.main()
