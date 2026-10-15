"""Diagnostico para download: o que o modulo disse, sem precisar de terminal.

Pensado para suporte a distancia: as ultimas linhas trocadas com cada
modulo, a identificacao que ele informa (firmware, MAC completo) e as
linhas de configuracao de motor, que a integracao ainda nao interpreta.
"""

from __future__ import annotations

import asyncio
import importlib
import unittest

from ha_falso import protocolo, relogio, sinais

diagnostics = importlib.import_module("controlart.diagnostics")

MAC = "AA-BB-CC"
ESTADO = "setcmd,AA-BB-CC,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0"


def rele(porta=4998):
    sinais.clear()
    relogio.agora = 0.0
    return protocolo.ModuloConexao(
        None, {"mac": MAC, "host": "127.0.0.1", "port": porta, "name": "Hubb M1"}
    )


class Linhas(unittest.TestCase):
    def test_guarda_as_linhas_recebidas_em_ordem(self):
        mod = rele()
        mod._trata_linha(ESTADO)
        mod._trata_linha("Parse Error!")
        linhas = [linha for _, sentido, linha in mod.linhas if sentido == "<-"]
        self.assertEqual(linhas, [ESTADO, "Parse Error!"])

    def test_guarda_so_as_ultimas(self):
        mod = rele()
        for n in range(protocolo.LINHAS_GUARDADAS + 10):
            mod._trata_linha(f"linha {n}")
        self.assertEqual(len(mod.linhas), protocolo.LINHAS_GUARDADAS)
        self.assertEqual(mod.linhas[-1][2], f"linha {protocolo.LINHAS_GUARDADAS + 9}")


class Identificacao(unittest.TestCase):
    def test_firmware(self):
        mod = rele()
        mod._trata_linha("VERSION 3.022")
        self.assertEqual(mod.firmware, "VERSION 3.022")

    def test_mac_completo(self):
        mod = rele()
        mod._trata_linha("MACADDR,00-1E-C0-AA-BB-CC")
        self.assertEqual(mod.mac_completo, "MACADDR,00-1E-C0-AA-BB-CC")

    def test_configuracao_de_motores(self):
        mod = rele()
        for _ in range(5):
            mod._trata_linha("setbmcb0md,AA-BB-CC,0,0,0,255")
        self.assertEqual(mod.motores, ["setbmcb0md,AA-BB-CC,0,0,0,255"] * 5)


class PedidoNaConexao(unittest.IsolatedAsyncioTestCase):
    async def test_pede_estado_firmware_e_mac(self):
        recebido: list[str] = []

        async def atende(reader, writer):
            while linha := await reader.readline():
                recebido.append(linha.decode("ascii").strip())
                writer.write(f"{ESTADO}\r\n".encode("ascii"))
                await writer.drain()
            writer.close()

        servidor = await asyncio.start_server(atende, "127.0.0.1", 0)
        async with servidor:
            mod = rele(servidor.sockets[0].getsockname()[1])
            sessao = asyncio.create_task(mod._sessao())
            await asyncio.sleep(0.2)
            sessao.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await sessao
        self.assertEqual(
            recebido, ["mdcmd_getmd,170,187,204", "get_firmware_version", "get_mac_addr"]
        )
        self.assertEqual(mod.conexoes, 1)


class Download(unittest.IsolatedAsyncioTestCase):
    async def test_um_bloco_por_modulo(self):
        mod = rele()
        mod._trata_linha(ESTADO)
        mod._trata_linha("VERSION 3.022")
        entrada = type("Entrada", (), {"runtime_data": type("Hub", (), {"modulos": {MAC: mod}})})
        dados = await diagnostics.async_get_config_entry_diagnostics(None, entrada)
        bloco = dados["modulos"][0]
        self.assertEqual(bloco["host"], "127.0.0.1")
        self.assertEqual(bloco["firmware"], "VERSION 3.022")
        self.assertEqual(bloco["tipo"], "relay")
        self.assertIn(ESTADO, [linha.split(" ", 2)[2] for linha in bloco["linhas"]])


if __name__ == "__main__":
    unittest.main()
