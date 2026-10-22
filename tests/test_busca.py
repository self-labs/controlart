"""Busca dos modulos na rede do HA, sem depender do roteador.

Num cliente (Deco), o navegador DHCP do HA nao mostrou nenhum modulo: a varredura
do HA depende de nome reverso no DNS do roteador. Aqui a integracao tenta a
porta 4998 em cada endereco, pergunta a quem atender e, depois, pergunta de
novo, com calma, aos aparelhos 00:60:37 que a tabela ARP mostrar. Testa a
lista de enderecos, a leitura da tabela ARP, a varredura, a busca de hora em
hora e os passos do cadastro que usam a busca.
"""

from __future__ import annotations

import sys
import unittest

from ha_falso import busca, config_flow, const, fluxos_criados, protocolo

RELE = protocolo.Identidade("AA-BB-CC", const.TIPO_RELE, 10)
DIMMER = protocolo.Identidade("DD-EE-FF", const.TIPO_DIMMER, 9)

ARP = """IP address       HW type     Flags       HW address            Mask     Device
192.168.1.21     0x1         0x2         00:60:37:aa:bb:cc     *        enp1s0
192.168.1.23     0x1         0x2         00:60:37:dd:ee:ff     *        enp1s0
192.168.1.50     0x1         0x2         f6:91:45:2d:2c:1f     *        enp1s0
192.168.1.77     0x1         0x0         00:00:00:00:00:00     *        enp1s0
"""


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

    def test_ip_fixo_gravado_com_mascara_32_busca_no_24(self):
        # um cliente, em 22/10/2026: IP fixo do HA com /32, modulos no mesmo /24
        hosts = busca.enderecos_da_rede("192.168.1.10", 32)
        self.assertEqual(len(hosts), 253)
        self.assertTrue({"192.168.1.21", "192.168.1.22", "192.168.1.23"} <= set(hosts))

    def test_mascara_menor_que_24_tambem_vira_24(self):
        self.assertEqual(len(busca.enderecos_da_rede("192.168.1.130", 26)), 253)

    def test_loopback_e_link_local_ficam_fora(self):
        self.assertEqual(busca.enderecos_da_rede("127.0.0.1", 8), [])
        self.assertEqual(busca.enderecos_da_rede("169.254.3.4", 16), [])


class TabelaArp(unittest.TestCase):
    def test_so_os_00_60_37_completos(self):
        self.assertEqual(busca.le_vizinhos(ARP), {
            "192.168.1.21": "00-60-37-AA-BB-CC",
            "192.168.1.23": "00-60-37-DD-EE-FF",
        })

    def test_sem_tabela(self):
        self.assertEqual(busca.le_vizinhos(""), {})


class Hass:
    """So o que a busca e o cadastro usam."""

    def __init__(self):
        self.gravado = []
        self.config_entries = self

    async def async_add_executor_job(self, funcao, *args):
        return funcao(*args)

    def async_update_entry(self, entrada, options):
        self.gravado.append(options)
        entrada.options = options


class ComRede(unittest.IsolatedAsyncioTestCase):
    """Rede falsa.

    `modulos` respondem como ControlArt; `abertos` atendem na porta mas nao sao
    modulos; `lentos` so respondem com a espera longa (a pergunta de novo, pelo
    ARP), nunca na primeira rodada; `arp` e o texto da tabela de vizinhos.
    """

    modulos: dict[str, protocolo.Identidade] = {}
    abertos: set[str] = set()
    lentos: set[str] = set()
    arp = ""

    def setUp(self):
        self._sonda = busca.sonda
        self._arp = busca._tabela_arp
        self._espera = busca.ESPERA_VIZINHO
        self._rede = sys.modules["homeassistant.components.network"].async_get_adapters
        fluxos_criados.clear()
        self.perguntas: list[tuple[str, float]] = []

        async def sonda(host, porta, timeout_conexao=const.TIMEOUT_SONDA):
            self.perguntas.append((host, timeout_conexao))
            if host in self.lentos and timeout_conexao < const.TIMEOUT_SONDA:
                raise protocolo.SemConexao
            if host in self.modulos:
                return self.modulos[host]
            if host in self.abertos:
                raise protocolo.SemResposta
            raise protocolo.SemConexao

        async def adaptadores(hass):
            return [
                {"enabled": True, "ipv4": [{"address": "192.168.1.10", "network_prefix": 24}]},
                {"enabled": False, "ipv4": [{"address": "172.30.32.1", "network_prefix": 23}]},
            ]

        busca.sonda = sonda
        busca._tabela_arp = lambda: self.arp
        busca.ESPERA_VIZINHO = 0
        sys.modules["homeassistant.components.network"].async_get_adapters = adaptadores

    def tearDown(self):
        busca.sonda = self._sonda
        busca._tabela_arp = self._arp
        busca.ESPERA_VIZINHO = self._espera
        sys.modules["homeassistant.components.network"].async_get_adapters = self._rede


class Varredura(ComRede):
    modulos = {"192.168.1.21": RELE, "192.168.1.23": DIMMER}
    abertos = {"192.168.1.30"}

    async def test_acha_so_quem_responde_como_controlart(self):
        resultado = await busca.varre(Hass(), await busca.enderecos(None))
        self.assertEqual(resultado.modulos, {"192.168.1.21": RELE, "192.168.1.23": DIMMER})
        self.assertEqual(resultado.sem_resposta, ["192.168.1.30"])

    async def test_uma_conexao_so_por_endereco(self):
        await busca.varre(Hass(), await busca.enderecos(None))
        hosts = [h for h, _ in self.perguntas]
        self.assertEqual(len(hosts), len(set(hosts)))
        self.assertTrue(all(t == busca.TIMEOUT_PORTA for _, t in self.perguntas))

    async def test_so_as_redes_ligadas_no_ha(self):
        hosts = await busca.enderecos(None)
        self.assertTrue(all(h.startswith("192.168.1.") for h in hosts))

    async def test_deixa_no_log_o_que_achou(self):
        with self.assertLogs("controlart.busca", "INFO") as log:
            await busca.varre(Hass(), await busca.enderecos(None))
        self.assertIn("2 modulo(s)", log.output[0])
        self.assertIn("192.168.1.30", log.output[0])


class PeloArp(ComRede):
    """O modulo nao atendeu na primeira rodada, mas o ARP mostrou o MAC dele."""

    modulos = {"192.168.1.21": RELE, "192.168.1.23": DIMMER}
    lentos = {"192.168.1.21"}
    arp = ARP

    async def test_pergunta_de_novo_com_calma_e_acha(self):
        resultado = await busca.varre(Hass(), await busca.enderecos(None))
        self.assertEqual(set(resultado.modulos), {"192.168.1.21", "192.168.1.23"})
        self.assertIn(("192.168.1.21", const.TIMEOUT_SONDA), self.perguntas)

    async def test_traz_o_mac_inteiro(self):
        resultado = await busca.varre(Hass(), await busca.enderecos(None))
        self.assertEqual(resultado.mac_visto("192.168.1.21"), "00-60-37-AA-BB-CC")

    async def test_aparelho_00_60_37_calado_fica_registrado(self):
        self.modulos = {"192.168.1.23": DIMMER}
        resultado = await busca.varre(Hass(), await busca.enderecos(None))
        self.assertEqual(resultado.sem_resposta, ["192.168.1.21"])
        tentativas = [t for h, t in self.perguntas if h == "192.168.1.21"]
        self.assertEqual(len(tentativas), 1 + busca.TENTATIVAS_VIZINHO)


class Entrada:
    def __init__(self, *modulos):
        self.options = {const.CONF_MODULOS: list(modulos)}


def cadastrado(mac, host):
    return {"host": host, "port": 4998, "mac": mac, "name": f"M {mac}", "keypad_inputs": []}


class BuscaDeHoraEmHora(ComRede):
    modulos = {"192.168.1.21": RELE, "192.168.1.40": DIMMER}
    arp = "IP address HW type Flags HW address Mask Device\n" \
          "192.168.1.40 0x1 0x2 00:60:37:dd:ee:ff * enp1s0\n"

    async def test_modulo_novo_vira_card_com_o_mac_do_arp(self):
        entrada = Entrada(cadastrado("AA-BB-CC", "192.168.1.21"))
        await busca.procura(Hass(), entrada)
        self.assertEqual(fluxos_criados, [{
            "dominio": "controlart",
            "context": {"source": "integration_discovery"},
            "data": {"host": "192.168.1.40", "mac": "DD-EE-FF",
                     const.CONF_TIPO: const.TIPO_DIMMER, const.CONF_SAIDAS: 9,
                     const.CONF_MAC_COMPLETO: "00-60-37-DD-EE-FF"},
        }])

    async def test_ip_do_cadastrado_nao_e_perguntado(self):
        await busca.procura(Hass(), Entrada(cadastrado("AA-BB-CC", "192.168.1.21")))
        self.assertNotIn("192.168.1.21", [h for h, _ in self.perguntas])

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
    modulos = {"192.168.1.21": RELE, "192.168.1.23": DIMMER}
    arp = ARP

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

    async def test_escolher_um_cria_a_entrada_com_o_mac_do_arp(self):
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
        self.assertEqual(modulo[const.CONF_MAC_COMPLETO], "00-60-37-DD-EE-FF")

    async def test_sem_nada_na_rede_pede_o_ip(self):
        self.modulos, self.arp = {}, ""
        passo = await self.fluxo().async_step_user()
        self.assertEqual((passo["type"], passo["step_id"]), ("form", "ip"))

    async def test_modulo_que_o_arp_viu_mas_calado_ja_vem_no_ip(self):
        self.modulos = {}
        fluxo = self.fluxo()
        captado = {}
        original = config_flow._esquema
        config_flow._esquema = lambda padrao: captado.update(padrao)
        try:
            passo = await fluxo.async_step_user()
        finally:
            config_flow._esquema = original
        self.assertEqual(passo["step_id"], "ip")
        self.assertEqual(captado["host"], "192.168.1.21")

    async def test_card_da_busca_de_hora_em_hora(self):
        fluxo = self.fluxo()
        passo = await fluxo.async_step_integration_discovery({
            "host": "192.168.1.23", "mac": "DD-EE-FF",
            const.CONF_TIPO: const.TIPO_DIMMER, const.CONF_SAIDAS: 9,
            const.CONF_MAC_COMPLETO: None,
        })
        self.assertEqual(passo["step_id"], "descoberto")
        self.assertEqual(fluxo.unique_id, "DD-EE-FF")
        self.assertEqual(passo["description_placeholders"],
                         {"mac": "00-60-37-DD-EE-FF", "host": "192.168.1.23"})
        fim = await fluxo.async_step_descoberto({"name": "Dimmer", "keypad_inputs": []})
        self.assertEqual(fim["type"], "create_entry")
        self.assertNotIn(const.CONF_MAC_COMPLETO, fim["options"][const.CONF_MODULOS][0])


class Opcoes(ComRede):
    modulos = {"192.168.1.21": RELE, "192.168.1.23": DIMMER}

    def opcoes(self, *modulos):
        fluxo = config_flow.OpcoesControlArt()
        fluxo.config_entry = Entrada(*modulos)
        fluxo.hass = Hass()
        return fluxo

    async def test_menu_comeca_por_procurar(self):
        menu = await self.opcoes().async_step_init()
        self.assertEqual(menu["menu_options"], ["procurar", "adicionar"])

    async def test_procurar_lista_so_os_nao_cadastrados(self):
        fluxo = self.opcoes(cadastrado("AA-BB-CC", "192.168.1.21"))
        passo = await fluxo.async_step_procurar()
        self.assertEqual(passo["step_id"], "procurar")
        self.assertEqual(list(fluxo._achados.modulos), ["192.168.1.23"])
        fim = await fluxo.async_step_procurar({"host": "192.168.1.23", "name": "", "keypad_inputs": []})
        macs = [m["mac"] for m in fim["data"][const.CONF_MODULOS]]
        self.assertEqual(macs, ["AA-BB-CC", "DD-EE-FF"])

    async def test_nada_novo_avisa(self):
        fluxo = self.opcoes(cadastrado("AA-BB-CC", "192.168.1.21"), cadastrado("DD-EE-FF", "192.168.1.23"))
        fim = await fluxo.async_step_procurar()
        self.assertEqual(fim, {"type": "abort", "reason": "nenhum_novo"})


if __name__ == "__main__":
    unittest.main()
