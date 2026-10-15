"""Modulo cabeado dimmer: mesmo transporte do rele, quadro e niveis proprios.

Quadro real, lido do dimmer de uma instalacao em 14/10/2026 com todos os
canais apagados (resposta a `mdcmd_getmd`):

    setdmmd,0D-95-23,1,0,0,0,0,1,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0

12 entradas, como no rele, e 9 canais com nivel de 0 a 255.
"""

from __future__ import annotations

import asyncio
import unittest

from ha_falso import EscritorFalso, const, light, protocolo, registro, relogio, sinais

MAC = "0D-95-23"
QUADRO_REAL = "setdmmd,0D-95-23,1,0,0,0,0,1,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0"
QUADRO_RELE = "setcmd,AA-BB-CC,0,1,0,0,0,0,0,0,0,0,0,0,1,0,1,0,0,0,0,0,0,0"


def dimmer(teclas=()):
    sinais.clear()
    relogio.agora = 0.0
    return protocolo.ModuloConexao(
        None,
        {
            "mac": MAC,
            "host": "x",
            "port": 4998,
            "name": "Dimmer",
            "keypad_inputs": list(teclas),
            const.CONF_TIPO: const.TIPO_DIMMER,
            const.CONF_SAIDAS: 9,
        },
    )


def quadro(mod, em: float, niveis=(0,) * 9, entradas=()) -> None:
    relogio.agora = em
    campos = ["1" if n in entradas else "0" for n in range(1, 13)]
    mod._trata_linha(",".join(["setdmmd", MAC, *campos, *map(str, niveis)]))


def conectado(mod):
    mod.conectado = True
    mod._writer = EscritorFalso()
    return mod._writer


async def confirmado(mod, acao, niveis):
    """Roda o comando e responde como o modulo, com o quadro de `niveis`."""
    tarefa = asyncio.create_task(acao)
    await asyncio.sleep(0)                               # o comando sai
    quadro(mod, relogio.agora + 5, niveis=niveis)
    await asyncio.wait_for(tarefa, 1)


async def responde_com(*linhas: str):
    """Modulo falso na porta local: responde ao primeiro comando com `linhas`."""

    async def atende(reader, writer):
        await reader.readline()
        for linha in linhas:
            writer.write(f"{linha}\r\n".encode("ascii"))
        await writer.drain()
        writer.close()

    servidor = await asyncio.start_server(atende, "127.0.0.1", 0)
    return servidor, servidor.sockets[0].getsockname()[1]


class Sonda(unittest.IsolatedAsyncioTestCase):
    async def test_reconhece_o_dimmer_pelo_quadro_real(self):
        servidor, porta = await responde_com(QUADRO_REAL)
        async with servidor:
            identidade = await protocolo.sonda("127.0.0.1", porta)
        self.assertEqual(identidade, (MAC, const.TIPO_DIMMER, 9))

    async def test_reconhece_o_rele(self):
        servidor, porta = await responde_com(QUADRO_RELE, "setbmcb0md,AA-BB-CC,0,0,0,255")
        async with servidor:
            identidade = await protocolo.sonda("127.0.0.1", porta)
        self.assertEqual(identidade, ("AA-BB-CC", const.TIPO_RELE, 10))

    async def test_recusa_quadro_sem_canais(self):
        servidor, porta = await responde_com("setdmmd,0D-95-23,0,0,0,0,0,0,0,0,0,0,0,0")
        async with servidor:
            with self.assertRaises(protocolo.SemResposta):
                await protocolo.sonda("127.0.0.1", porta)


class Estado(unittest.TestCase):
    def test_quadro_real_vira_estado(self):
        mod = dimmer()
        mod._trata_linha(QUADRO_REAL)
        self.assertTrue(mod.tem_estado)
        self.assertEqual(mod.saidas, [0] * 9)
        self.assertEqual(mod.entradas, [1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0])

    def test_nivel_de_cada_canal(self):
        mod = dimmer()
        quadro(mod, 0.0)
        quadro(mod, 10.0, niveis=(128, 0, 0, 0, 0, 0, 0, 0, 255))
        self.assertEqual(mod.saidas[0], 128)
        self.assertEqual(mod.saidas[8], 255)

    def test_ignora_quadro_de_rele(self):
        mod = dimmer()
        mod._trata_linha("setcmd,0D-95-23,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1")
        self.assertFalse(mod.tem_estado)

    def test_rele_ignora_quadro_de_dimmer(self):
        sinais.clear()
        rele = protocolo.ModuloConexao(
            None, {"mac": MAC, "host": "x", "port": 4998, "name": "Rele"}
        )
        rele._trata_linha(QUADRO_REAL)
        self.assertFalse(rele.tem_estado)

    def test_tecla_no_dimmer(self):
        mod = dimmer(teclas=[2])
        quadro(mod, 0.0)
        quadro(mod, 10.0, entradas=[2])
        quadro(mod, 10.5)
        quadro(mod, 20.0, entradas=[2])
        self.assertEqual(sinais.count(f"controlart_tecla_{MAC}_2"), 2)


class Comando(unittest.IsolatedAsyncioTestCase):
    async def test_nivel_vai_no_mesmo_sendrele_do_rele(self):
        mod = dimmer()
        quadro(mod, 0.0)
        escritor = conectado(mod)
        await confirmado(mod, mod.envia_nivel(1, 128), (128, 0, 0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(escritor.enviado, ["mdcmd_sendrele,13,149,35,0,128\r\n"])

    async def test_nivel_arredondado_pelo_modulo_vale_o_do_quadro(self):
        mod = dimmer()
        quadro(mod, 0.0)
        conectado(mod)
        await confirmado(mod, mod.envia_nivel(1, 128), (102, 0, 0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(light.CanalDimmer(mod, 1).brightness, 102)

    async def test_ultimo_canal(self):
        mod = dimmer()
        escritor = conectado(mod)
        await mod.envia_nivel(9, 0)
        self.assertEqual(escritor.enviado, ["mdcmd_sendrele,13,149,35,8,0\r\n"])

    async def test_canal_fora_da_faixa(self):
        mod = dimmer()
        conectado(mod)
        with self.assertRaises(ValueError):
            await mod.envia_nivel(10, 255)

    async def test_nivel_fora_da_faixa(self):
        mod = dimmer()
        conectado(mod)
        with self.assertRaises(ValueError):
            await mod.envia_nivel(1, 256)


class Luz(unittest.IsolatedAsyncioTestCase):
    def test_dispositivo_se_apresenta_como_dimmer(self):
        canal = light.CanalDimmer(dimmer(), 1)
        self.assertEqual(canal._attr_device_info["model"], "Módulo Cabeado Dimmer")

    def test_brilho_e_o_nivel_do_modulo(self):
        mod = dimmer()
        quadro(mod, 0.0, niveis=(102, 0, 0, 0, 0, 0, 0, 0, 0))
        canal = light.CanalDimmer(mod, 1)
        self.assertTrue(canal.is_on)
        self.assertEqual(canal.brightness, 102)
        self.assertFalse(light.CanalDimmer(mod, 2).is_on)

    async def test_ligar_com_brilho(self):
        mod = dimmer()
        quadro(mod, 0.0)
        escritor = conectado(mod)
        acao = light.CanalDimmer(mod, 3).async_turn_on(brightness=153)
        await confirmado(mod, acao, (0, 0, 153, 0, 0, 0, 0, 0, 0))
        self.assertEqual(escritor.enviado, ["mdcmd_sendrele,13,149,35,2,153\r\n"])

    async def test_ligar_sem_brilho_volta_ao_ultimo_nivel(self):
        mod = dimmer()
        quadro(mod, 0.0, niveis=(204, 0, 0, 0, 0, 0, 0, 0, 0))
        quadro(mod, 10.0)                                 # apagou pela parede
        escritor = conectado(mod)
        acao = light.CanalDimmer(mod, 1).async_turn_on()
        await confirmado(mod, acao, (204, 0, 0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(escritor.enviado, ["mdcmd_sendrele,13,149,35,0,204\r\n"])

    async def test_ligar_sem_brilho_nunca_visto_acende_tudo(self):
        mod = dimmer()
        quadro(mod, 0.0)
        escritor = conectado(mod)
        acao = light.CanalDimmer(mod, 1).async_turn_on()
        await confirmado(mod, acao, (255, 0, 0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(escritor.enviado, ["mdcmd_sendrele,13,149,35,0,255\r\n"])

    async def test_desligar(self):
        mod = dimmer()
        quadro(mod, 0.0, niveis=(255, 0, 0, 0, 0, 0, 0, 0, 0))
        escritor = conectado(mod)
        await confirmado(mod, light.CanalDimmer(mod, 1).async_turn_off(), (0,) * 9)
        self.assertEqual(escritor.enviado, ["mdcmd_sendrele,13,149,35,0,0\r\n"])


class Registro(unittest.TestCase):
    def test_uma_luz_por_canal_do_dimmer(self):
        alvo = registro.esperado(
            [{"mac": MAC, const.CONF_TIPO: const.TIPO_DIMMER, const.CONF_SAIDAS: 9}]
        )
        luzes = sorted(uid for dominio, uid in alvo if dominio == "light")
        self.assertEqual(len(luzes), 9)
        self.assertEqual(luzes[-1], f"controlart_{MAC}_luz_09")

    def test_rele_cadastrado_antes_do_dimmer_continua_com_10(self):
        alvo = registro.esperado([{"mac": "AA-BB-CC"}])
        self.assertEqual(sum(1 for dominio, _ in alvo if dominio == "light"), 10)


if __name__ == "__main__":
    unittest.main()
