[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5?logo=home-assistant&logoColor=white)](https://hacs.xyz/) [![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.1%2B-41BDF5?logo=home-assistant&logoColor=white)](https://www.home-assistant.io/) [![Release](https://img.shields.io/github/v/release/self-labs/controlart?color=293a44)](https://github.com/self-labs/controlart/releases) [![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://github.com/self-labs/controlart/blob/master/LICENSE)

<!-- Todo link da linha acima fica absoluto. O HACS reescreve um link relativo prefixando
o primeiro "(" da linha inteira, que é a imagem do primeiro badge. -->

# ControlArt para Home Assistant

Integração local para os **módulos cabeados da ControlArt**, configurados pelo mdConfig: o **relé** (10 saídas a relé, 12 entradas digitais) e o **dimmer** (canais com nível de 0 a 255, 12 entradas digitais). Fala direto com cada módulo por TCP na rede local: sem nuvem, sem Node-RED, sem outro Home Assistant no meio.

_English summary below._

## O que aparece no Home Assistant

Cada módulo vira um dispositivo com:

| Entidade        | Quantas                             | Para quê                                                                           |
| --------------- | ----------------------------------- | ---------------------------------------------------------------------------------- |
| `light`         | 10 no relé, uma por canal no dimmer | As saídas. Liga e desliga (com brilho, no dimmer), e o estado vem sempre do módulo |
| `event`         | uma por tecla de keypad             | Dispara um evento a cada toque, para usar em automações                            |
| `binary_sensor` | uma por entrada de interruptor      | A posição da alavanca (diagnóstico, desligada por padrão)                          |
| `binary_sensor` | 1                                   | Se o módulo está respondendo                                                       |
| `sensor`        | 1                                   | O endereço IP do módulo (diagnóstico), visível mesmo com ele fora do ar            |
| `button`        | 2                                   | "Acender tudo" e "Apagar tudo": o módulo inteiro com um comando só                 |

O card do dispositivo mostra o **firmware** e o **MAC inteiro**, como o mdConfig e a etiqueta da caixa (por exemplo 3.027 e `00:60:37:aa:bb:cc`). O módulo só informa os três últimos bytes do MAC; os três primeiros, `00-60-37`, são iguais em todo módulo ControlArt.

A página da integração também oferece **Baixar diagnóstico**: as últimas linhas trocadas com cada módulo, o firmware e o MAC que ele informa, e quantas vezes a conexão caiu. Serve para suporte a distância, sem terminal na rede da instalação.

Os interruptores e keypads da parede continuam funcionando como sempre: quem aciona as saídas é o módulo. O Home Assistant enxerga tudo o que acontece e manda comandos junto, sem um cancelar o outro.

## Instalação

### HACS (recomendado)

[![Abrir este repositório no HACS do seu Home Assistant.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=self-labs&repository=controlart&category=integration)

O botão abre este repositório direto no seu HACS. Clique em **Baixar** e reinicie o Home Assistant.

Ele funciona pelo [my.home-assistant.io](https://my.home-assistant.io/), que só sabe chegar na sua instância depois que você informa o endereço dela uma vez, em **Configurações → Sistema → Rede → URL do Home Assistant**. Até lá, ele pergunta.

<details>
<summary>Fazendo à mão</summary>

1. HACS → menu ⋮ → **Repositórios personalizados**.
2. URL `https://github.com/self-labs/controlart`, categoria **Integração** → **Adicionar**.
3. Abra o repositório e clique em **Baixar**.
4. Reinicie o Home Assistant.

</details>

### À mão

Copie a pasta `custom_components/controlart` para dentro de `config/custom_components/` e reinicie.

## Configuração

### Primeiro módulo

[![Começar o cadastro da integração ControlArt no seu Home Assistant.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=controlart)

O botão abre o cadastro direto. Sem ele: _Configurações → Dispositivos e serviços → Adicionar integração → ControlArt._

1. A integração **procura os módulos na rede** do Home Assistant: tenta a porta 4998 em cada endereço e pergunta a quem atender. Leva alguns segundos.
2. **Escolher um módulo encontrado na rede**: cada um aparece com o MAC da etiqueta da caixa e do mdConfig, e o IP em que respondeu. O tipo (relé ou dimmer) e as saídas o módulo já informou.
3. Dê um **nome** e marque quais **entradas são teclas de keypad** (pulsadores). As demais são tratadas como interruptores comuns.

Se nenhum módulo responder, ou se você escolher **Informar o IP**, o cadastro pede o IP e a porta (4998, salvo se você mudou no mdConfig).

### Os outros módulos

Com o primeiro cadastrado, a integração repete a busca ao iniciar e a cada hora. Cada módulo que ela achar e que ainda não estiver cadastrado aparece em _Dispositivos e serviços_ como **Descoberto**, um card por módulo com o MAC dele: **Configurar**, nome e teclas. **Ignorar** num card vale só para aquele módulo.

Para não esperar a próxima busca: na integração, **Configurar → Procurar módulos na rede**. **Adicionar pelo IP** continua lá, para um módulo em outra porta ou outra rede.

O Home Assistant também mostra o card sozinho quando vê o módulo pedir IP ao roteador, o que acontece quando o módulo liga, se ele estiver com DHCP no mdConfig: o manifest pede ao HA os aparelhos com o início de MAC `00-60-37`. Esse início é do fabricante do chip e outro aparelho pode ter, por isso a integração pergunta na porta 4998 antes de mostrar o card.

### Depois do cadastro

O nome das saídas começa como "Saída 1", "Saída 2"… Renomeie no próprio Home Assistant e ponha cada uma na sua área; a integração não mexe no que você ajustou.

Um **IP fixo** para cada módulo (reserva no roteador ou IP estático no mdConfig) continua recomendado. Se o IP de um módulo cadastrado mudar, a busca de hora em hora o acha no endereço novo e corrige o cadastro; até lá, o módulo fica indisponível.

## Dicas

- **Tecla de keypad numa automação**: use o gatilho de _estado_ na entidade `event`. Cada toque muda o estado para o horário do toque. Filtre `not_to: [unknown, unavailable]` para não disparar quando o Home Assistant reinicia. Dois toques seguidos na mesma tecla precisam de pouco mais de 1 s entre eles para virar dois eventos.
- **Interruptor comum numa automação**: a posição da alavanca **não** diz se a luz está acesa. O módulo inverte a saída a cada movimento, então as duas coisas se desencontram. Dispare em _qualquer_ mudança do sensor da entrada e use `toggle`.
- **Cenas do keypad**: o módulo executa a cena programada no mdConfig quando a tecla é apertada na parede. Não existe comando para disparar essa cena remotamente. Para acioná-la pelo Home Assistant, reproduza-a num script.
- **Dimmer aceso sem brilho escolhido** (botão, voz, "acender a sala"): o canal volta ao último nível em que ficou aceso desde que o Home Assistant iniciou; se nunca acendeu, vai ao máximo. Os degraus de uma transição não contam: apagar devagar e acender de novo volta ao nível de antes.
- **Transição no dimmer** (`transition` em `light.turn_on` e `light.turn_off`): a integração faz a rampa, um nível de cada vez, com pelo menos 0,2 s entre os degraus. O serviço volta na hora; um comando novo no mesmo canal cancela a rampa.
- **Comando que o módulo não confirma** vira erro no Home Assistant em vez de passar em silêncio. Um módulo que para de responder derruba a conexão e as entidades ficam indisponíveis até ele voltar.
- **Script que acende várias luzes em sequência**: ponha `continue_on_error: true` nas ações de luz. Sem isso, um comando não confirmado interrompe o resto do script.

## Limitações

- Motores e cortinas configurados no módulo são ignorados: o comando de motor não é conhecido. As linhas de configuração de motor que o módulo manda aparecem no diagnóstico.
- A integração não altera a programação do módulo; isso continua sendo feito no mdConfig.
- A busca só percorre as redes marcadas em _Configurações → Sistema → Rede_, até 1024 endereços por rede (numa rede maior, só os 254 vizinhos do Home Assistant), e só na porta 4998. Um Home Assistant em Docker precisa de `network_mode: host` para enxergar a rede da casa. Módulo em outra VLAN ou em outra porta entra pelo IP.
- O número de série da caixa não aparece no card: nenhum comando conhecido do módulo devolve o serial.

O protocolo, com as armadilhas que apareceram pelo caminho, está descrito em [docs/protocolo.md](docs/protocolo.md).

Os testes rodam sem o Home Assistant instalado, só com a biblioteca padrão: `python -m unittest discover -s tests`.

## Versões

As versões seguem o calendário (`AAAA.M.R`: ano, mês e a revisão dentro do mês), não o versionamento semântico. O que mudou em cada uma está no [CHANGELOG.md](CHANGELOG.md). O HACS oferece cada versão nova como atualização.

## Créditos

Inspirado na integração [tompsonpecini/controlart](https://github.com/tompsonpecini/controlart), de **Tompson Pecini**, de onde este projeto partiu (licença MIT, mantida em [LICENSE](https://github.com/self-labs/controlart/blob/master/LICENSE)). Os comandos de firmware, MAC e "tudo aceso/apagado" vieram do driver Hubitat [hhorigian/hubitat_Controlart_Relays](https://github.com/hhorigian/hubitat_Controlart_Relays).

O ícone e o logo da integração são a marca da [ControlArt](https://www.controlart.com.br/), tirados do site dela, e servem só para identificar o fabricante dos módulos. Este projeto não é da ControlArt nem tem o apoio dela.

---

## English summary

Local-push Home Assistant integration for **ControlArt wired modules**: the relay module (10 relay outputs, 12 digital inputs) and the dimmer module (channels with a 0 to 255 level, 12 digital inputs). Each module becomes a device with one `light` entity per output (with brightness on the dimmer), one `event` entity per keypad push button, one diagnostic `binary_sensor` per switch input, a connectivity sensor, a diagnostic IP sensor, and "All on" / "All off" buttons for the whole module. The device card shows the module firmware and its full MAC, and **Download diagnostics** returns the last lines exchanged with each module. Setup searches the Home Assistant network for modules on port 4998 and lists the ones that answer, so only a name and the keypad inputs are asked. Once the first module is set up, the search runs at startup and every hour: new modules show up as discovered cards, and a configured module whose IP changed is followed. Home Assistant's own DHCP discovery (MAC prefix `00:60:37`) also shows a card when a module requests an address at power-up. Modules on another port or network are added by IP. Wall switches and keypads keep working through the module itself; Home Assistant follows every change and can switch outputs alongside them.

Install with the HACS button above (or add `https://github.com/self-labs/controlart` as a custom repository, type Integration), restart, then use the setup button to pick the first module from the search. Versions are CalVer (`YYYY.M.R`), listed in [CHANGELOG.md](CHANGELOG.md).

Inspired by [tompsonpecini/controlart](https://github.com/tompsonpecini/controlart) by Tompson Pecini, where this project started (MIT).

Not affiliated with ControlArt. Use at your own risk.
