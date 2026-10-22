"""Busca dos modulos na rede do HA, sem depender do roteador.

O HA so ve um modulo pelo DHCP quando ele pede IP (ao ligar), e a varredura
de hora em hora do HA (aiodiscover) so devolve aparelho que tenha nome reverso
(PTR) no DNS do roteador, o que roteador domestico costuma nao ter: num cliente
(Deco), em 21/10/2026, o navegador DHCP do HA nao mostrou nenhum modulo.

Entao a integracao procura ela mesma, em duas frentes:
1. Tenta a porta 4998 em cada endereco da rede do HA e, na mesma conexao,
   pergunta quem e (sonda). Uma conexao so por endereco: o modulo e um
   aparelho embarcado e ja tem as conexoes do HA ou do Node-RED abertas.
2. Essa tentativa faz o sistema perguntar o MAC de cada endereco (ARP). Depois
   dela, a tabela de vizinhos do sistema (/proc/net/arp) tem o MAC de todo
   aparelho ligado, e os que comecam com 00:60:37 sao perguntados de novo,
   com calma. Isso acha o modulo mesmo que ele nao atenda na primeira rodada,
   e da o MAC inteiro.
A 2026.10.5 nao achou os modulos de um cliente porque o IP fixo do HA estava com
mascara /32 e a busca percorreu zero enderecos (enderecos_da_rede). Cada busca
deixa no log o que encontrou, para o proximo caso aparecer de cara.

Roda no cadastro, nas opcoes e, com a integracao ja configurada, ao iniciar e
a cada hora: modulo novo vira card de descoberto, modulo cadastrado que mudou
de IP tem o IP corrigido.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import ipaddress
import logging
from pathlib import Path
from typing import Any

from homeassistant.components import network
from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY, ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery_flow

from .const import (
    CONF_MAC_COMPLETO,
    CONF_MODULOS,
    CONF_SAIDAS,
    CONF_TIPO,
    DOMAIN,
    PORTA_PADRAO,
    PREFIXO_MAC,
)
from .protocolo import Identidade, SemConexao, SemResposta, mac_da_rede, sonda

_LOGGER = logging.getLogger(__name__)

MAX_ENDERECOS = 1024    # um /22, a rede padrao do Deco; maior que isso, so o /24 do HA
TIMEOUT_PORTA = 1.0     # s · endereco sem ninguem nao responde: desiste e segue
# tentativas ao mesmo tempo: um /22 em uns 8 s. Cada endereco sem ninguem ocupa uma linha
# incompleta na tabela ARP por uns 3 s, e a tabela do Linux para em 1024 linhas.
SIMULTANEOS = 128
TENTATIVAS_VIZINHO = 2  # perguntas a um aparelho 00:60:37 que nao atendeu na primeira rodada
ESPERA_VIZINHO = 1.0    # s · entre essas perguntas
TABELA_ARP = Path("/proc/net/arp")


@dataclass
class Resultado:
    """O que uma busca achou."""

    modulos: dict[str, Identidade] = field(default_factory=dict)   # ip -> identidade
    macs: dict[str, str] = field(default_factory=dict)             # ip -> MAC 00:60:37 do ARP
    sem_resposta: list[str] = field(default_factory=list)          # 00:60:37 ou porta aberta, calado

    def mac_visto(self, host: str) -> str | None:
        return self.macs.get(host)


async def enderecos(hass: HomeAssistant) -> list[str]:
    """Os enderecos das redes IPv4 que o HA usa (Configuracoes > Sistema > Rede)."""
    hosts: list[str] = []
    for adaptador in await network.async_get_adapters(hass):
        if not adaptador["enabled"]:
            continue
        for ip in adaptador["ipv4"]:
            hosts += enderecos_da_rede(ip["address"], ip["network_prefix"])
    return list(dict.fromkeys(hosts))


def enderecos_da_rede(proprio: str, prefixo: int) -> list[str]:
    """Os outros enderecos da rede de `proprio`, de um /24 a MAX_ENDERECOS.

    Mascara menor que /24 vira /24: num cliente o IP fixo do HA foi gravado com
    mascara /32 (22/10/2026), a rede "do HA" era so ele, e a busca da
    2026.10.5 percorreu zero enderecos. Os modulos respondiam pelo roteador.
    """
    ip = ipaddress.ip_address(proprio)
    if ip.is_loopback or ip.is_link_local:
        return []
    rede = ipaddress.ip_network(f"{proprio}/{prefixo}", strict=False)
    if prefixo > 24 or rede.num_addresses > MAX_ENDERECOS:
        rede = ipaddress.ip_network(f"{proprio}/24", strict=False)
    return [str(h) for h in rede.hosts() if h != ip]


def le_vizinhos(texto: str) -> dict[str, str]:
    """{ip: MAC} dos aparelhos 00:60:37 completos na tabela ARP do Linux."""
    prefixo = PREFIXO_MAC.replace("-", ":").lower()
    vizinhos: dict[str, str] = {}
    for linha in texto.splitlines()[1:]:
        campos = linha.split()
        # IP, tipo de hardware, flags (0x2 = completo), MAC, mascara, interface
        if len(campos) >= 4 and campos[2] != "0x0" and campos[3].lower().startswith(prefixo):
            vizinhos[campos[0]] = mac_da_rede(campos[3])
    return vizinhos


def _tabela_arp() -> str:
    try:
        return TABELA_ARP.read_text(encoding="ascii")
    except OSError:
        return ""   # fora do Linux (nos testes, no Windows) nao ha tabela


async def varre(hass: HomeAssistant, hosts: list[str], porta: int = PORTA_PADRAO) -> Resultado:
    """Procura os modulos em `hosts`; ver o comentario do arquivo."""
    resultado = Resultado()
    limite = asyncio.Semaphore(SIMULTANEOS)

    async def um(host: str) -> None:
        async with limite:
            try:
                resultado.modulos[host] = await sonda(host, porta, TIMEOUT_PORTA)
            except SemConexao:
                pass                                # ninguem, ou a porta fechada
            except SemResposta:
                resultado.sem_resposta.append(host)  # atendeu, mas nao como modulo

    await asyncio.gather(*(um(h) for h in hosts))

    alvo = set(hosts)
    resultado.macs = {
        ip: mac
        for ip, mac in le_vizinhos(await hass.async_add_executor_job(_tabela_arp)).items()
        if ip in alvo
    }
    for host in resultado.macs:
        if host in resultado.modulos:
            continue
        for _ in range(TENTATIVAS_VIZINHO):
            try:
                resultado.modulos[host] = await sonda(host, porta)
                break
            except (SemConexao, SemResposta):
                await asyncio.sleep(ESPERA_VIZINHO)
        else:
            if host not in resultado.sem_resposta:
                resultado.sem_resposta.append(host)

    _LOGGER.info(
        "ControlArt: busca em %d enderecos na porta %d: %d modulo(s) %s; MAC 00:60:37 no ARP: %s; "
        "sem resposta de modulo: %s",
        len(hosts), porta, len(resultado.modulos),
        sorted(resultado.modulos), resultado.macs or "nenhum", sorted(resultado.sem_resposta) or "nenhum",
    )
    return resultado


async def procura(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Modulo novo vira card de descoberto; cadastrado em outro IP tem o IP corrigido."""
    modulos: list[dict[str, Any]] = list(entry.options.get(CONF_MODULOS, []))
    # o IP de um cadastrado esta ocupado pela conexao dele: nao precisa perguntar
    ocupados = {m[CONF_HOST] for m in modulos}
    resultado = await varre(hass, [h for h in await enderecos(hass) if h not in ocupados])
    por_mac = {m[CONF_MAC]: m for m in modulos}
    mudou: dict[str, str] = {}
    for host, identidade in resultado.modulos.items():
        if identidade.mac in por_mac:
            mudou[identidade.mac] = host
            continue
        discovery_flow.async_create_flow(
            hass,
            DOMAIN,
            context={"source": SOURCE_INTEGRATION_DISCOVERY},
            data={
                CONF_HOST: host,
                CONF_MAC: identidade.mac,
                CONF_TIPO: identidade.tipo,
                CONF_SAIDAS: identidade.saidas,
                CONF_MAC_COMPLETO: resultado.mac_visto(host),
            },
        )
    if mudou:
        for mac, host in mudou.items():
            _LOGGER.info("ControlArt %s mudou de IP: %s -> %s",
                         por_mac[mac].get("name", mac), por_mac[mac][CONF_HOST], host)
        novos = [{**m, CONF_HOST: mudou[m[CONF_MAC]]} if m[CONF_MAC] in mudou else m for m in modulos]
        # a entrada recarrega e os modulos voltam nos enderecos certos
        hass.config_entries.async_update_entry(entry, options={**entry.options, CONF_MODULOS: novos})
