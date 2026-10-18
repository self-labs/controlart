# Changelog

Todas as mudanças relevantes da integração ControlArt ficam registradas neste arquivo.

O formato segue o [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).
As versões seguem o **CalVer `AAAA.M.R`** (ano, mês sem zero à esquerda, revisão dentro do mês)
e **não** o versionamento semântico: `2026.10.1` diz quando saiu, nada sobre compatibilidade.
As versões `1.0.0` e `1.0.1` são do projeto original de Tompson Pecini, de onde este partiu.

## [Unreleased]

## [2026.10.2] - 2026-10-18

### 🐛 Fixed

- **O MAC voltou ao card do dispositivo.** A 2026.10.1 trouxe do projeto original a remoção dele e ainda apagava o MAC dos dispositivos já cadastrados no primeiro início. O MAC (os três bytes que o módulo informa, os mesmos do mdConfig) é o que diz qual módulo é qual, e fica no card. Quem chegou a rodar a 2026.10.1 recebe o MAC de volta no primeiro início.

## [2026.10.1] - 2026-10-18

Primeira versão como projeto próprio da Self-Labs, inspirado no
[tompsonpecini/controlart](https://github.com/tompsonpecini/controlart).

### ✨ Added

- **Módulo dimmer**: o cadastro reconhece o tipo pelo cabeçalho `setdmmd` e o número de canais pelo tamanho do quadro. Cada canal vira uma `light` com brilho de 0 a 255, enviado direto ao módulo (128 é 128, conferido em módulo real). Ligado sem brilho escolhido, volta ao último nível aceso desde que o Home Assistant iniciou, ou ao máximo.
- **Transição no dimmer** (`transition` em `light.turn_on` e `light.turn_off`): rampa feita pela integração, um nível de cada vez, com pelo menos 0,2 s entre degraus, cancelada por um comando novo no mesmo canal.
- **Sensor de diagnóstico com o endereço IP** de cada módulo, visível mesmo com o módulo fora do ar.
- **Botões "Acender tudo" e "Apagar tudo"** por módulo, com um comando só (`mdcmd_setallonmd` e `mdcmd_setalloffmd`), esperando o quadro de confirmação.
- **Diagnóstico para download**: as últimas 50 linhas trocadas com cada módulo nos dois sentidos, as conexões e quedas, as linhas de configuração de motor e as respostas de firmware e MAC, para suporte a distância.
- **Firmware no card do dispositivo**, no formato do mdConfig (3.027 nos relés, 1.021 no dimmer).
- **Botões do My Home Assistant no README**, para abrir o repositório no HACS e começar o cadastro.
- **Testes** com `unittest` e um Home Assistant falso, rodando no CI junto com `hassfest` e a validação do HACS.

### 🔧 Changed

- **Projeto próprio**: `codeowners`, `documentation` e `issue_tracker` apontam para `self-labs/controlart`, e o botão do HACS no README abre este repositório. Quem instalou como repositório personalizado do HACS não precisa trocar nada.
- **Versões em CalVer**, publicadas como releases do GitHub: o HACS oferece cada versão nova como atualização, em vez de um commit.
- **Comando que o módulo não confirma em 3 s vira erro** no Home Assistant, em vez de passar em silêncio.
- **Módulo mudo derruba a conexão**: sem resposta ao `getmd` em 10 s, a sessão cai e a integração reconecta, e as entidades ficam indisponíveis até o módulo voltar.

### 🐛 Fixed

- **Tecla de keypad perdia o segundo toque**: o quadro de limpeza não zerava as teclas, e dois toques seguidos sem limpeza no meio também se perdiam porque o módulo não avisa quando a tecla é solta. Agora as teclas zeram na limpeza e, depois de cada toque, a integração pede o estado a cada segundo, até 5 vezes, até ver a tecla solta.
- **Estado velho depois de uma queda**: o módulo volta a contar como sem estado conhecido quando a conexão cai.
- **Apagar o dimmer com transição deixava um degrau da rampa como "último nível"** (20% numa rampa de 1 s), e acender sem brilho parecia não acender. Os degraus da rampa não contam mais.
- **Os três bytes que o módulo informa entravam como MAC de rede** (`CONNECTION_NETWORK_MAC`), que o Home Assistant usa para juntar aparelhos de integrações diferentes. Continuam como identificador do dispositivo e no diagnóstico. Nos dispositivos cadastrados antes, o MAC velho sai do registro no primeiro início, porque o Home Assistant soma `connections` e nunca tira sozinho.
- **Firmware vazio**: o módulo responde só o número (`3027`), não `VERSION...` como no driver Hubitat.
- **Aviso de `device_registry.async_get_device` obsoleto** no HA 2026.10: o dispositivo é procurado entre os da própria entrada.

## [1.0.1] - 2026-10-04

### ✨ Added

- Ícone da integração (`brand/`).

## [1.0.0] - 2026-09-21

### ✨ Added

- Integração local para o módulo cabeado a relé: uma `light` por saída, `event` por tecla de keypad, `binary_sensor` por entrada de interruptor e de conexão, cadastro pelo IP.

[Unreleased]: https://github.com/self-labs/controlart/compare/v2026.10.2...HEAD
[2026.10.2]: https://github.com/self-labs/controlart/compare/v2026.10.1...v2026.10.2
[2026.10.1]: https://github.com/self-labs/controlart/compare/v1.0.1...v2026.10.1
[1.0.1]: https://github.com/self-labs/controlart/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/self-labs/controlart/releases/tag/v1.0.0
