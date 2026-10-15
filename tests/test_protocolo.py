"""Testes da leitura dos quadros setcmd, sem Home Assistant instalado.

O Home Assistant entra como modulos falsos: o que interessa aqui e a regra do
quadro de limpeza e a borda de subida das teclas, que vivem em protocolo.py.

Rodar da raiz do repositorio:

    python -m unittest discover -s tests
"""

from __future__ import annotations

import unittest

from ha_falso import protocolo, relogio, sinais

MAC = "AA-BB-CC"


def modulo(teclas=()):
    sinais.clear()
    return protocolo.ModuloConexao(
        None, {"mac": MAC, "host": "x", "port": 4998, "name": "Teste", "keypad_inputs": list(teclas)}
    )


def quadro(mod, em: float, entradas=(), saidas=()) -> None:
    relogio.agora = em
    campos = ["1" if n in entradas else "0" for n in range(1, 13)]
    campos += ["1" if n in saidas else "0" for n in range(1, 11)]
    mod._trata_setcmd(campos)


def toques(entrada: int) -> int:
    return sinais.count(f"controlart_tecla_{MAC}_{entrada}")


class TeclaDeKeypad(unittest.TestCase):
    def test_tecla_repetida_que_alterna_uma_saida(self):
        mod = modulo(teclas=[1])
        quadro(mod, 0.0)                                  # getmd da conexao
        quadro(mod, 10.0, entradas=[1], saidas=[1])       # 1o toque
        quadro(mod, 10.5, saidas=[1])                     # limpeza
        quadro(mod, 20.0, entradas=[1])                   # 2o toque, saida apaga
        quadro(mod, 20.5)                                 # limpeza
        self.assertEqual(toques(1), 2)

    def test_tecla_repetida_sem_saida_vinculada(self):
        mod = modulo(teclas=[2])
        quadro(mod, 0.0)
        quadro(mod, 10.0, entradas=[2])
        quadro(mod, 10.5)
        quadro(mod, 20.0, entradas=[2])
        quadro(mod, 20.5)
        self.assertEqual(toques(2), 2)

    def test_teclas_alternadas(self):
        mod = modulo(teclas=[1, 2])
        quadro(mod, 0.0)
        quadro(mod, 10.0, entradas=[1])
        quadro(mod, 10.5)
        quadro(mod, 20.0, entradas=[2])
        quadro(mod, 20.5)
        quadro(mod, 30.0, entradas=[1])
        quadro(mod, 30.5)
        self.assertEqual((toques(1), toques(2)), (2, 1))

    def test_toque_depois_do_keepalive(self):
        mod = modulo(teclas=[1])
        quadro(mod, 0.0)
        quadro(mod, 10.0, entradas=[1])
        quadro(mod, 10.5)
        quadro(mod, 130.5)                                # resposta ao getmd de 120 s
        quadro(mod, 140.0, entradas=[1])
        quadro(mod, 140.5)
        self.assertEqual(toques(1), 2)

    def test_quadro_de_limpeza_nao_dispara_tecla(self):
        mod = modulo(teclas=[1])
        quadro(mod, 0.0)
        quadro(mod, 10.0, entradas=[1])
        quadro(mod, 10.5)
        quadro(mod, 10.9)                                 # quadro repetido, nada mudou
        self.assertEqual(toques(1), 1)


class Interruptor(unittest.TestCase):
    def test_limpeza_nao_mexe_na_alavanca(self):
        mod = modulo()
        quadro(mod, 0.0)
        quadro(mod, 10.0, entradas=[3], saidas=[3])
        quadro(mod, 10.5, saidas=[3])                     # limpeza
        self.assertEqual(mod.entradas[2], 1)
        quadro(mod, 20.0)                                 # alavanca volta, saida apaga
        quadro(mod, 20.5)
        self.assertEqual(mod.entradas[2], 0)

    def test_limpeza_com_tecla_preserva_interruptor(self):
        mod = modulo(teclas=[1])
        quadro(mod, 0.0, entradas=[5])                    # interruptor ja fechado
        quadro(mod, 10.0, entradas=[1, 5])                # toque na tecla
        quadro(mod, 10.5)                                 # limpeza zera tudo no quadro
        self.assertEqual(mod.entradas[0], 0)              # tecla volta a 0
        self.assertEqual(mod.entradas[4], 1)              # interruptor continua fechado


if __name__ == "__main__":
    unittest.main()
