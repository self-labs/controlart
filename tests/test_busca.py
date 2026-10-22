"""Busca dos modulos na rede do HA, sem depender do roteador.

Na Dora (Deco), o navegador DHCP do HA nao mostrou nenhum modulo: a varredura
do HA depende de nome reverso no DNS do roteador. Aqui a integracao tenta a
porta 4998 em cada endereco e pergunta a quem atender. Testa a lista de
enderecos, a varredura, a busca de hora em hora e os passos do cadastro que
usam a busca.
"""

from __future__ import annotations

import sys
import unittest

from ha_falso import busca, config_flow, const, fluxos_criados, protocolo

RELE = protocolo.Identidade("AA-BB-CC", const.TIPO_RELE, 10)
DIMMER = protocolo.Identidade("DD-EE-FF", const.TIPO_DIMMER, 9)


class Enderecos(unittest.TestCase):
    def test_rede_24_sem_o_proprio_ha(self):
        hosts = busca.enderecos_da_rede("192.168.1.10", 24)
        self.assertEqual(len(hosts), 253)
        self.assertNotIn("192.168.1.10", hosts)
        self.assertEqual(hosts[0], "192.168.1.1")

    def test_rede_do_deco_22_inteira(self):
        hosts = busca.enderecos_da_rede("192.168.68.8", 22)
        self.assertEqual(len(hosts), 1021)
        self.assertIn("192.168.71.254", hosts)

    def test_rede_grande_demais_fica_no_24_do_ha(self):
        hosts = busca.enderecos_da_rede("10.1.2.3", 16)
        self.assertEqual(hosts[0], "10.1.2.1")
        self.assertEqual(len(hosts), 253)

    def test_loopback_e_link_local_ficam_fora(self):
        self.assertEqual(busca.enderecos_da_rede("127.0.0.1", 8), [])
        self.assertEqual(busca.enderecos_da_rede("169.254.3.4", 16), [])


class ComRede(unittest.IsolatedAsyncioTestCase):
    """Rede falsa: `abertos` tem a porta 4998 aberta, `modulos` respondem como ControlArt."""

    abertos: set[str] = set()
    modulos: dict[str, protocolo.Identidade] = {}

    def setUp(self):
        self._porta = busca._porta_aberta
        self._sonda = busca.sonda
        self._rede = sys.modules["homeassistant.components.network"].async_get_adapters
        fluxos_criados.clear()

        async def porta(host, porta):
            return host in self.abertos

        async def sonda(host, porta):
            if host not in self.modulos:
                raise protocolo.SemResposta
            return self.modulos[host]

        async def adaptadores(hass):
            return [
                {"enabled": True, "ipv4": [{"address": "192.168.1.10", "network_prefix": 24}]},
                {"enabled": False, "ipv4": [{"address": "172.30.32.1", "network_prefix": 23}]},
            ]

        busca._porta_aberta = porta
        busca.sonda = sonda
        sys.modules["homeassistant.components.network"].async_get_adapters = adaptadores

    def tearDown(self):
        busca._porta_aberta = self._porta
        busca.sonda = self._sonda
        sys.modules["homeassistant.components.network"].async_get_adapters = self._rede


class Varredura(ComRede):
    abertos = {"192.168.1.21", "192.168.1.23", "192.168.1.30"}
    modulos = {"192.168.1.21": RELE, "192.168.1.23": DIMMER}

    async def test_acha_so_quem_responde_como_controlart(self):
        # .30 tem a porta aberta, mas nao e um modulo
        achados = await busca.varre(await busca.enderecos(None))
        self.assertEqual(achados, {"192.168.1.21": RELE, "192.168.1.23": DIMMER})

    async def test_so_as_redes_ligadas_no_ha(self):
        hosts = await busca.enderecos(None)
        self.assertTrue(all(h.startswith("192.168.1.") for h in hosts))


class Entrada:
    def __init__(self, *modulos):
        self.options = {const.CONF_MODULOS: list(modulos)}


class Hass:
    def __init__(self):
        self.gravado = []
        self.config_entries = self

    def async_update_entry(self, entrada, options):
        self.gravado.append(options)
        entrada.options = options


def cadastrado(mac, host):
    return {"host": host, "port": 4998, "mac": mac, "name": f"M {mac}", "keypad_inputs": []}


class BuscaDeHoraEmHora(ComRede):
    abertos = {"192.168.1.21", "192.168.1.40"}
    modulos = {"192.168.1.21": RELE, "192.168.1.40": DIMMER}

    async def test_modulo_novo_vira_card(self):
        entrada = Entrada(cadastrado("AA-BB-CC", "192.168.1.21"))
        await busca.procura(Hass(), entrada)
        self.assertEqual(fluxos_criados, [{
            "dominio": "controlart",
            "context": {"source": "integration_discovery"},
            "data": {"host": "192.168.1.40", "mac": "DD-EE-FF",
                     const.CONF_TIPO: const.TIPO_DIMMER, const.CONF_SAIDAS: 9},
        }])

    async def test_cadastrado_em_outro_ip_e_corrigido(self):
        entrada = Entrada(cadastrado("AA-BB-CC", "192.168.1.99"), cadastrado("DD-EE-FF", "192.168.1.40"))
        hass = Hass()
        await busca.procura(hass, entrada)
        self.assertEqual(fluxos_criados, [])
        hosts = [m["host"] for m in entrada.options[const.CONF_MODULOS]]
        self.assertEqual(hosts, ["192.168.1.21", "192.168.1.40"])
        self.assertEqual(len(hass.gravado), 1)

    async def test_nada_mudou_nao_grava(self):
        entrada = Entrada(cadastrado("AA-BB-CC", "192.168.1.21"), cadastrado("DD-EE-FF", "192.168.1.40"))
        hass = Hass()
        await busca.procura(hass, entrada)
        self.assertEqual((fluxos_criados, hass.gravado), ([], []))


class Cadastro(ComRede):
    abertos = {"192.168.1.21", "192.168.1.23"}
    modulos = {"192.168.1.21": RELE, "192.168.1.23": DIMMER}

    def fluxo(self):
        fluxo = config_flow.ControlArtConfigFlow()
        fluxo.context = {}
        fluxo.entradas = []
        fluxo.ignorados = set()
        fluxo.hass = Hass()
        return fluxo

    async def test_adicionar_integracao_oferece_os_encontrados(self):
        passo = await self.fluxo().async_step_user()
        self.assertEqual(passo["type"], "menu")
        self.assertEqual(passo["menu_options"], ["escolher", "ip"])
        self.assertEqual(passo["description_placeholders"], {"quantos": "2"})

    async def test_escolher_um_cria_a_entrada(self):
        fluxo = self.fluxo()
        await fluxo.async_step_user()
        self.assertEqual((await fluxo.async_step_escolher())["step_id"], "escolher")
        fim = await fluxo.async_step_escolher(
            {"host": "192.168.1.23", "name": "Dimmer", "keypad_inputs": ["2"]}
        )
        self.assertEqual(fim["type"], "create_entry")
        modulo = fim["options"][const.CONF_MODULOS][0]
        self.assertEqual((modulo["host"], modulo["mac"], modulo[const.CONF_TIPO], modulo[const.CONF_SAIDAS]),
                         ("192.168.1.23", "DD-EE-FF", const.TIPO_DIMMER, 9))
        self.assertEqual(modulo[const.CONF_TECLAS], [2])
        self.assertNotIn(const.CONF_MAC_COMPLETO, modulo)   # so o DHCP ve o MAC inteiro

    async def test_sem_nada_na_rede_pede_o_ip(self):
        self.modulos = {}
        passo = await self.fluxo().async_step_user()
        self.assertEqual((passo["type"], passo["step_id"]), ("form", "ip"))

    async def test_card_da_busca_de_hora_em_hora(self):
        fluxo = self.fluxo()
        passo = await fluxo.async_step_integration_discovery({
            "host": "192.168.1.23", "mac": "DD-EE-FF",
            const.CONF_TIPO: const.TIPO_DIMMER, const.CONF_SAIDAS: 9,
        })
        self.assertEqual(passo["step_id"], "descoberto")
        self.assertEqual(fluxo.unique_id, "DD-EE-FF")
        self.assertEqual(passo["description_placeholders"],
                         {"mac": "00-60-37-DD-EE-FF", "host": "192.168.1.23"})
        fim = await fluxo.async_step_descoberto({"name": "Dimmer", "keypad_inputs": []})
        self.assertEqual(fim["type"], "create_entry")
        self.assertNotIn(const.CONF_MAC_COMPLETO, fim["options"][const.CONF_MODULOS][0])


class Opcoes(ComRede):
    abertos = {"192.168.1.21", "192.168.1.23"}
    modulos = {"192.168.1.21": RELE, "192.168.1.23": DIMMER}

    def opcoes(self, *modulos):
        fluxo = config_flow.OpcoesControlArt()
        fluxo.config_entry = Entrada(*modulos)
        fluxo.hass = None
        return fluxo

    async def test_menu_comeca_por_procurar(self):
        menu = await self.opcoes().async_step_init()
        self.assertEqual(menu["menu_options"], ["procurar", "adicionar"])

    async def test_procurar_lista_so_os_nao_cadastrados(self):
        fluxo = self.opcoes(cadastrado("AA-BB-CC", "192.168.1.21"))
        passo = await fluxo.async_step_procurar()
        self.assertEqual(passo["step_id"], "procurar")
        self.assertEqual(list(fluxo._achados), ["192.168.1.23"])
        fim = await fluxo.async_step_procurar({"host": "192.168.1.23", "name": "", "keypad_inputs": []})
        macs = [m["mac"] for m in fim["data"][const.CONF_MODULOS]]
        self.assertEqual(macs, ["AA-BB-CC", "DD-EE-FF"])

    async def test_nada_novo_avisa(self):
        fluxo = self.opcoes(cadastrado("AA-BB-CC", "192.168.1.21"), cadastrado("DD-EE-FF", "192.168.1.23"))
        fim = await fluxo.async_step_procurar()
        self.assertEqual(fim, {"type": "abort", "reason": "nenhum_novo"})


if __name__ == "__main__":
    unittest.main()
