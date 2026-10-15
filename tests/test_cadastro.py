"""Cadastro: o que a sonda descobre vai para a configuracao do modulo."""

from __future__ import annotations

import unittest

from ha_falso import config_flow, const, protocolo

DIMMER = protocolo.Identidade("0D-95-23", const.TIPO_DIMMER, 9)


def sonda_que_responde(identidade):
    async def sonda(host, porta):
        return identidade

    return sonda


class Cadastro(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._sonda = config_flow.sonda

    def tearDown(self):
        config_flow.sonda = self._sonda

    async def test_dimmer_guarda_tipo_e_canais(self):
        config_flow.sonda = sonda_que_responde(DIMMER)
        modulo, erro = await config_flow._monta_modulo(
            {"host": "192.168.68.23", "port": 4998, "name": "Dimmer", "keypad_inputs": []}, []
        )
        self.assertIsNone(erro)
        self.assertEqual(modulo["mac"], "0D-95-23")
        self.assertEqual(modulo[const.CONF_TIPO], const.TIPO_DIMMER)
        self.assertEqual(modulo[const.CONF_SAIDAS], 9)

    async def test_editar_so_o_nome_de_um_rele_antigo(self):
        async def sonda_proibida(host, porta):
            raise AssertionError("nao precisa perguntar ao modulo")

        config_flow.sonda = sonda_proibida
        antigo = {"host": "10.0.0.5", "port": 4998, "mac": "AA-BB-CC", "name": "M1",
                  "keypad_inputs": []}
        modulo, erro = await config_flow._monta_modulo(
            {"host": "10.0.0.5", "port": 4998, "name": "Hubb M1", "keypad_inputs": []}, [], antigo
        )
        self.assertIsNone(erro)
        self.assertEqual(modulo[const.CONF_TIPO], const.TIPO_RELE)
        self.assertEqual(modulo[const.CONF_SAIDAS], const.N_SAIDAS)


if __name__ == "__main__":
    unittest.main()
