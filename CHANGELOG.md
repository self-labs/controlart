# Changelog

Todas as mudanças relevantes da integração ControlArt ficam registradas neste arquivo.

O formato segue o [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).
As versões seguem o **CalVer `AAAA.M.R`** (ano, mês sem zero à esquerda, revisão dentro do mês)
e **não** o versionamento semântico: `2026.10.1` diz quando saiu, nada sobre compatibilidade.
As versões `1.0.0` e `1.0.1` são do projeto original de Tompson Pecini, de onde este partiu.

## [Unreleased]

## [2026.10.6] - 2026-10-22

### 🔧 Changed

- **O README explica o caminho sem nenhum clique**: numa rede UniFi, com a integração UniFi Network no Home Assistant, ela informa ao HA o IP e o MAC de cada aparelho a cada início, e o reconhecimento pelo início `00-60-37` (desde a 2026.10.4) abre o card de cada módulo sozinho. Conferido no código do HA (`device_tracker/entity.py` avisa a descoberta DHCP até dos rastreadores criados desligados); ainda não testado com módulos numa rede UniFi.

### 🐛 Fixed

- **A busca da 2026.10.5 não achou os módulos de um cliente** e o cadastro abriu direto no pedido de IP. Causa, vista no servidor dele: o IP fixo do Home Assistant foi gravado com máscara /32, então a rede "do HA" era só ele mesmo e a busca percorreu zero endereços. Os módulos respondiam normalmente, pelo roteador. Agora uma máscara menor que /24 (como /32) vira o /24 do IP do HA. Com o código novo rodado no próprio servidor do cliente, a busca achou os três módulos em 2 s.
- **A busca ficou mais robusta**, nos pontos que apareceram enquanto a causa não era conhecida:
  - **Uma conexão só por endereço.** A 2026.10.5 abria uma conexão para ver a porta, fechava e abria outra para perguntar. O módulo é um aparelho embarcado, muitas vezes com as conexões do Node-RED abertas; agora a pergunta vai na mesma conexão.
  - **Segunda rodada pela tabela ARP.** A tentativa em cada endereço faz o sistema aprender o MAC dos aparelhos da rede. Os que começam com `00:60:37` são perguntados de novo, com 5 s de espera e duas tentativas, e trazem o MAC inteiro para o card. Não ajuda num servidor como o desse cliente, que fala com a rede só pelo roteador.
  - **Menos tentativas ao mesmo tempo** (128, eram 256), para não encher a tabela ARP do sistema, que para em 1024 linhas: um /22 leva uns 8 s.
  - **Cada busca deixa uma linha no log** (`ControlArt: busca em N enderecos…`): quantos endereços, os módulos achados, os aparelhos `00:60:37` que o ARP mostrou e quem atendeu sem responder como módulo. "busca em 0 enderecos" teria mostrado o problema na hora.
  - Um aparelho `00:60:37` que o ARP mostrou mas que não respondeu já vem preenchido no pedido de IP.

## [2026.10.5] - 2026-10-21

### ✨ Added

- **O cadastro procura os módulos na rede.** Em **Adicionar integração**, a integração tenta a porta 4998 em cada endereço da rede do Home Assistant (alguns segundos) e lista os módulos que responderem, com o MAC da etiqueta e o IP. Basta escolher, dar o nome e marcar as teclas; **Informar o IP** continua como alternativa. Em **Configurar**, **Procurar módulos na rede** faz o mesmo para os módulos seguintes.
- **Busca de hora em hora.** Com a integração configurada, a mesma busca roda ao iniciar e a cada hora: um módulo novo aparece como card de **Descoberto**, e um módulo cadastrado que mudou de IP volta sozinho no endereço novo.

### 🐛 Fixed

- **Nenhum card aparecia depois de instalar e reiniciar.** A 2026.10.4 contava com o Home Assistant achando os módulos pelo início do MAC, mas o HA só vê o módulo quando ele pede IP ao ligar: a varredura de hora em hora do HA só devolve aparelho com nome reverso no DNS do roteador, o que roteador doméstico não costuma ter. Num cliente (Deco), o navegador DHCP do HA não mostrou nenhum módulo. A busca da própria integração resolve, e o reconhecimento pelo MAC continua para quando o módulo liga.

## [2026.10.4] - 2026-10-21

### ✨ Added

- **Os módulos aparecem sozinhos depois de instalar e reiniciar.** O Home Assistant reconhece o módulo pelo início do MAC, `00-60-37`, igual em todo módulo ControlArt, e mostra um card de **Descoberto** por módulo em Dispositivos e serviços. O IP, o tipo e as saídas o módulo já informou: o card só pede o nome e as entradas de keypad. O primeiro card cria a integração e os seguintes entram nela; **Ignorar** vale só para aquele módulo. Funciona também com IP fixo no mdConfig, porque o Home Assistant varre a rede ao iniciar e a cada hora. Esse início de MAC é da NXP, a fabricante do chip, então a integração pergunta ao aparelho na porta 4998 antes de mostrar o card, e o que não responder como ControlArt não aparece. O cadastro pelo IP continua, para módulo em outra porta ou outra rede.
- **Um módulo cadastrado que muda de IP volta sozinho.** Quando o Home Assistant vê o módulo em outro endereço, a integração troca o IP do cadastro e reconecta. O IP fixo continua recomendado, mas deixou de ser obrigatório.

### 🔧 Changed

- **O card do dispositivo mostra o MAC inteiro**, como o mdConfig e a etiqueta da caixa, em vez de só os três últimos bytes que o módulo informa. Os dispositivos já cadastrados trocam o MAC curto pelo inteiro no primeiro início; os ids das entidades não mudam. O diagnóstico também traz o MAC inteiro.

## [2026.10.3] - 2026-10-21

### 🔧 Changed

- **O ícone e o logo são os oficiais da ControlArt.** Saíram do logo horizontal do site do fabricante: os dois círculos no ícone e a marca inteira no logo. O tema escuro ganhou versões próprias (`dark_icon`, `dark_logo`) com o anel verde e o disco branco, como no site; no tema claro ficam o anel cinza e o disco verde do favicon deles. O README diz de quem é a marca.
- **O README abre com os badges dos outros projetos**: HACS, a versão mínima do Home Assistant (2025.1), a versão atual e a licença.

### 🐛 Fixed

- **O link da licença nos Créditos não abria dentro do HACS.** O HACS só reescreve um link relativo quando nada depois dele na mesma linha tem `://`, e o link do Hubitat vinha logo depois. O link agora é absoluto.

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

[Unreleased]: https://github.com/self-labs/controlart/compare/v2026.10.6...HEAD
[2026.10.6]: https://github.com/self-labs/controlart/compare/v2026.10.5...v2026.10.6
[2026.10.5]: https://github.com/self-labs/controlart/compare/v2026.10.4...v2026.10.5
[2026.10.4]: https://github.com/self-labs/controlart/compare/v2026.10.3...v2026.10.4
[2026.10.3]: https://github.com/self-labs/controlart/compare/v2026.10.2...v2026.10.3
[2026.10.2]: https://github.com/self-labs/controlart/compare/v2026.10.1...v2026.10.2
[2026.10.1]: https://github.com/self-labs/controlart/compare/v1.0.1...v2026.10.1
[1.0.1]: https://github.com/self-labs/controlart/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/self-labs/controlart/releases/tag/v1.0.0
