"""Busca dos modulos na rede do HA, sem depender do roteador.

O HA so ve um modulo pelo DHCP quando ele pede IP (ao ligar), e a varredura
de hora em hora do HA (aiodiscover) so devolve aparelho que tenha nome reverso
(PTR) no DNS do roteador, o que roteador domestico costuma nao ter: na Dora
(Deco), em 21/10/2026, o navegador DHCP do HA nao mostrou nenhum modulo.

Entao a integracao procura ela mesma: tenta a porta 4998 em cada endereco da
rede do HA e consulta (sonda) quem atender. Roda no cadastro, nas opcoes e,
com a integracao ja configurada, ao iniciar e a cada hora: modulo novo vira
card de descoberto, modulo cadastrado que mudou de IP tem o IP corrigido.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
from typing import Any

from homeassistant.components import network
from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY, ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery_flow

from .const import CONF_MODULOS, CONF_SAIDAS, CONF_TIPO, DOMAIN, PORTA_PADRAO
from .protocolo import Identidade, SemConexao, SemResposta, sonda

_LOGGER = logging.getLogger(__name__)

MAX_ENDERECOS = 1024    # um /22, a rede padrao do Deco; maior que isso, so o /24 do HA
TIMEOUT_PORTA = 1.0     # s · endereco sem ninguem nao responde: desiste e segue
SIMULTANEOS = 256       # tentativas ao mesmo tempo: um /22 em uns 4 s


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
    """Os outros enderecos da rede de `proprio`, sem passar de MAX_ENDERECOS."""
    ip = ipaddress.ip_address(proprio)
    if ip.is_loopback or ip.is_link_local:
        return []
    rede = ipaddress.ip_network(f"{proprio}/{prefixo}", strict=False)
    if rede.num_addresses > MAX_ENDERECOS:
        rede = ipaddress.ip_network(f"{proprio}/24", strict=False)
    return [str(h) for h in rede.hosts() if h != ip]


async def _porta_aberta(host: str, porta: int) -> bool:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, porta), TIMEOUT_PORTA)
    except (OSError, asyncio.TimeoutError):
        return False
    writer.close()
    return True


async def varre(hosts: list[str], porta: int = PORTA_PADRAO) -> dict[str, Identidade]:
    """{ip: identidade} de quem respondeu como modulo ControlArt."""
    limite = asyncio.Semaphore(SIMULTANEOS)

    async def um(host: str) -> tuple[str, Identidade] | None:
        async with limite:
            if not await _porta_aberta(host, porta):
                return None
        try:
            return host, await sonda(host, porta)
        except (SemConexao, SemResposta):
            # a porta abriu, mas nao e um modulo (ou nao respondeu a tempo)
            return None

    achados = await asyncio.gather(*(um(h) for h in hosts))
    return dict(a for a in achados if a)


async def procura(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Modulo novo vira card de descoberto; cadastrado em outro IP tem o IP corrigido."""
    modulos: list[dict[str, Any]] = list(entry.options.get(CONF_MODULOS, []))
    # o IP de um cadastrado esta ocupado pela conexao dele: nao precisa perguntar
    ocupados = {m[CONF_HOST] for m in modulos}
    achados = await varre([h for h in await enderecos(hass) if h not in ocupados])
    por_mac = {m[CONF_MAC]: m for m in modulos}
    mudou: dict[str, str] = {}
    for host, identidade in achados.items():
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
            },
        )
    if mudou:
        for mac, host in mudou.items():
            _LOGGER.info("ControlArt %s mudou de IP: %s -> %s",
                         por_mac[mac].get("name", mac), por_mac[mac][CONF_HOST], host)
        novos = [{**m, CONF_HOST: mudou[m[CONF_MAC]]} if m[CONF_MAC] in mudou else m for m in modulos]
        # a entrada recarrega e os modulos voltam nos enderecos certos
        hass.config_entries.async_update_entry(entry, options={**entry.options, CONF_MODULOS: novos})
