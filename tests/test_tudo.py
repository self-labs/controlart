"""Botoes "Acender tudo" e "Apagar tudo" de cada modulo.

Comandos do driver Hubitat da ControlArt (hhorigian/hubitat_Controlart_Relays):
`mdcmd_setallonmd,<endereco>` e `mdcmd_setalloffmd,<endereco>`. Com endereco,
valem so para aquele modulo; o `setmaster*` sem endereco fica de fora porque
pode pegar todos os modulos da instalacao.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import unittest

from ha_falso import PACOTE, EscritorFalso, HomeAssistantError, protocolo, registro, relogio, sinais

button = importlib.import_module("controlart.button")

MAC = "AA-BB-CC"


def rele(saidas=()):
    sinais.clear()
    relogio.agora = 0.0
    mod = protocolo.ModuloConexao(
        None, {"mac": MAC, "host": "x", "port": 4998, "name": "Hubb M1"}
    )
    quadro(mod, saidas)
    mod.conectado = True
    mod._writer = EscritorFalso()
    return mod


def quadro(mod, saidas):
    relogio.agora += 5
    campos = ["0"] * 12 + ["1" if n in saidas else "0" for n in range(1, 11)]
    mod._trata_linha(",".join(["setcmd", MAC, *campos]))


async def apertado(mod, botao, saidas_depois):
    tarefa = asyncio.create_task(botao.async_press())
    await asyncio.sleep(0)
    quadro(mod, saidas_depois)
    await asyncio.wait_for(tarefa, 1)


class Botoes(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._prazo = protocolo.TIMEOUT_CONFIRMACAO
        protocolo.TIMEOUT_CONFIRMACAO = 0.1

    def tearDown(self):
        protocolo.TIMEOUT_CONFIRMACAO = self._prazo

    async def test_apagar_tudo(self):
        mod = rele(saidas=[1, 4])
        await apertado(mod, button.ApagarTudo(mod), saidas_depois=[])
        self.assertEqual(mod._writer.enviado, ["mdcmd_setalloffmd,170,187,204\r\n"])
        self.assertEqual(mod.saidas, [0] * 10)

    async def test_acender_tudo(self):
        mod = rele()
        await apertado(mod, button.AcenderTudo(mod), saidas_depois=range(1, 11))
        self.assertEqual(mod._writer.enviado, ["mdcmd_setallonmd,170,187,204\r\n"])

    async def test_ja_apagado_nao_espera(self):
        mod = rele()
        await asyncio.wait_for(button.ApagarTudo(mod).async_press(), 0.05)
        self.assertEqual(mod._writer.enviado, ["mdcmd_setalloffmd,170,187,204\r\n"])

    async def test_sem_confirmacao_vira_erro(self):
        mod = rele(saidas=[2])
        with self.assertRaises(HomeAssistantError):
            await button.ApagarTudo(mod).async_press()

    async def test_desconectado_vira_erro(self):
        mod = rele(saidas=[2])
        mod.conectado = False
        with self.assertRaises(HomeAssistantError):
            await button.ApagarTudo(mod).async_press()


class Cadastro(unittest.TestCase):
    def test_registro_nao_apaga_os_botoes(self):
        alvo = registro.esperado([{"mac": MAC}])
        self.assertIn(("button", f"controlart_{MAC}_acender_tudo"), alvo)
        self.assertIn(("button", f"controlart_{MAC}_apagar_tudo"), alvo)

    def test_nome_em_todos_os_idiomas(self):
        chaves = [button.AcenderTudo._attr_translation_key, button.ApagarTudo._attr_translation_key]
        for arquivo in ["strings.json", "translations/en.json", "translations/pt-BR.json"]:
            textos = json.loads((PACOTE / arquivo).read_text(encoding="utf-8"))
            for chave in chaves:
                with self.subTest(arquivo=arquivo, chave=chave):
                    self.assertTrue(textos["entity"]["button"][chave]["name"])


if __name__ == "__main__":
    unittest.main()
