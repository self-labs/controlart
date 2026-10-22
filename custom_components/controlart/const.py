"""Constantes da integracao ControlArt."""

DOMAIN = "controlart"

PORTA_PADRAO = 4998
# Tres primeiros bytes do MAC, iguais em todo modulo (bloco da NXP, o fabricante do chip).
# O modulo so informa os outros tres. E por eles que o HA acha os modulos na rede (manifest).
PREFIXO_MAC = "00-60-37"
INTERVALO_GETMD = 120          # s · pedido periodico de estado, serve de keepalive
INTERVALO_BUSCA = 3600         # s · busca de modulos novos e de IP mudado na rede (busca.py)
JANELA_LIMPEZA = 2.0           # s · quadro com entradas zeradas logo apos outro
RECONEXAO_MAX = 30             # s · teto da espera progressiva
TIMEOUT_SONDA = 5.0            # s · para o modulo responder ao ser cadastrado
TIMEOUT_RESPOSTA = 10.0        # s · para responder ao getmd; sem resposta, reconecta
TIMEOUT_CONFIRMACAO = 3.0      # s · para o quadro que confirma um comando

N_SAIDAS = 10                  # do rele; o dimmer informa os canais no proprio quadro
N_ENTRADAS = 12

# tipo do modulo, reconhecido pelo cabecalho do quadro de estado
TIPO_RELE = "relay"
TIPO_DIMMER = "dimmer"
CABECALHOS = {"setcmd": TIPO_RELE, "setdmmd": TIPO_DIMMER}

# chaves da configuracao guardada na entrada
CONF_MODULOS = "modules"
CONF_TECLAS = "keypad_inputs"   # entradas ligadas a teclas de keypad (pulsadores)
CONF_TIPO = "module_type"       # ausente nos cadastros anteriores ao dimmer: rele
CONF_SAIDAS = "outputs"         # saidas ou canais; ausente: N_SAIDAS
CONF_MAC_COMPLETO = "full_mac"  # MAC inteiro visto pela descoberta; ausente: PREFIXO_MAC + mac

SIGNAL_ESTADO = "controlart_estado_{}"      # por mac
SIGNAL_TECLA = "controlart_tecla_{}_{}"     # por mac, entrada
SIGNAL_CONEXAO = "controlart_conexao_{}"    # por mac
SIGNAL_IDENTIDADE = "controlart_identidade_{}"  # por mac: firmware informado pelo modulo
