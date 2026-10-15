"""Conexao: prova de vida, confirmacao dos comandos e estado na queda.

Os servidores aqui fazem as vezes do modulo na porta local, com prazos
encurtados para o teste nao esperar os 120 s do keepalive de verdade.
"""

from __future__ import annotations

import asyncio
import unittest

from ha_falso import EscritorFalso, HomeAssistantError, protocolo, relogio, sinais

MAC = "AA-BB-CC"
ESTADO = "setcmd,AA-BB-CC,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0"


def rele(porta=4998):
    sinais.clear()
    relogio.agora = 0.0
    return protocolo.ModuloConexao(
        None, {"mac": MAC, "host": "127.0.0.1", "port": porta, "name": "Teste"}
    )


def quadro(mod, saidas=()):
    campos = ["0"] * 12 + ["1" if n in saidas else "0" for n in range(1, 11)]
    mod._trata_linha(",".join(["setcmd", MAC, *campos]))


async def modulo_falso(responde: bool):
    """Aceita a conexao; se `responde`, devolve o estado a cada comando."""

    async def atende(reader, writer):
        while await reader.readline():
            if responde:
                writer.write(f"{ESTADO}\r\n".encode("ascii"))
                await writer.drain()
        writer.close()

    servidor = await asyncio.start_server(atende, "127.0.0.1", 0)
    return servidor, servidor.sockets[0].getsockname()[1]


class ProvaDeVida(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._prazos = protocolo.INTERVALO_GETMD, protocolo.TIMEOUT_RESPOSTA
        protocolo.INTERVALO_GETMD = 0.05
        protocolo.TIMEOUT_RESPOSTA = 0.05

    def tearDown(self):
        protocolo.INTERVALO_GETMD, protocolo.TIMEOUT_RESPOSTA = self._prazos

    async def test_modulo_mudo_derruba_a_sessao(self):
        servidor, porta = await modulo_falso(responde=False)
        async with servidor:
            with self.assertRaises(ConnectionError):
                await asyncio.wait_for(rele(porta)._sessao(), 1)

    async def test_modulo_que_responde_mantem_a_sessao(self):
        servidor, porta = await modulo_falso(responde=True)
        async with servidor:
            mod = rele(porta)
            sessao = asyncio.create_task(mod._sessao())
            await asyncio.sleep(0.3)                     # varios ciclos de keepalive
            self.assertFalse(sessao.done())
            self.assertTrue(mod.conectado)
            sessao.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await sessao


class Queda(unittest.TestCase):
    def test_estado_velho_nao_sobrevive_a_queda(self):
        mod = rele()
        mod.conectado = True
        quadro(mod, saidas=[1])
        mod._marca_desconectado()
        self.assertFalse(mod.tem_estado)


class Confirmacao(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._prazo = protocolo.TIMEOUT_CONFIRMACAO
        protocolo.TIMEOUT_CONFIRMACAO = 0.1

    def tearDown(self):
        protocolo.TIMEOUT_CONFIRMACAO = self._prazo

    def conectado(self):
        mod = rele()
        quadro(mod)
        mod.conectado = True
        mod._writer = EscritorFalso()
        return mod

    async def test_comando_confirmado_pelo_modulo(self):
        mod = self.conectado()
        comando = asyncio.create_task(mod.envia_rele(3, True))
        await asyncio.sleep(0)                           # o comando sai
        quadro(mod, saidas=[3])                          # e o modulo confirma
        await asyncio.wait_for(comando, 1)
        self.assertEqual(mod.saidas[2], 1)

    async def test_comando_sem_confirmacao_vira_erro(self):
        mod = self.conectado()
        with self.assertRaises(HomeAssistantError):
            await mod.envia_rele(3, True)

    async def test_comando_que_nao_muda_nada_nao_espera(self):
        mod = self.conectado()
        await asyncio.wait_for(mod.envia_rele(3, False), 0.05)
        self.assertEqual(mod._writer.enviado, ["mdcmd_sendrele,170,187,204,2,0\r\n"])


if __name__ == "__main__":
    unittest.main()
