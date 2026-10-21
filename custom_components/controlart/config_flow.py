"""Cadastro dos modulos pela interface.

So o IP e pedido: o modulo e perguntado pelo endereco de difusao e responde
com o proprio MAC, que e o endereco dos comandos. O cabecalho da resposta diz
se e rele ou dimmer, e o tamanho dela, quantas saidas tem. O primeiro modulo
entra no fluxo de configuracao; os demais, pelas opcoes (Configurar).

Descoberta: o manifest pede ao HA os aparelhos com MAC 00:60:37 (PREFIXO_MAC).
O HA ve o pedido DHCP de cada um e varre a rede a cada hora, entao o modulo
aparece como descoberto mesmo com IP fixo no mdConfig. O prefixo e da NXP e
outro aparelho pode ter, por isso o modulo e perguntado antes de virar card.
Um modulo ja cadastrado nao vira card: so tem o IP atualizado, se mudou.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_MAC_COMPLETO,
    CONF_MODULOS,
    CONF_SAIDAS,
    CONF_TECLAS,
    CONF_TIPO,
    DOMAIN,
    N_ENTRADAS,
    N_SAIDAS,
    PORTA_PADRAO,
    TIPO_RELE,
)
from .protocolo import Identidade, SemConexao, SemResposta, mac_da_rede, sonda

SELETOR_TECLAS = SelectSelector(
    SelectSelectorConfig(
        options=[str(n) for n in range(1, N_ENTRADAS + 1)],
        multiple=True,
        mode=SelectSelectorMode.LIST,
    )
)


def _esquema(padrao: dict[str, Any]) -> vol.Schema:
    host = {"default": padrao[CONF_HOST]} if padrao.get(CONF_HOST) else {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, **host): str,
            vol.Required(CONF_PORT, default=padrao.get(CONF_PORT, PORTA_PADRAO)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=65535)
            ),
            vol.Required(CONF_NAME, default=padrao.get(CONF_NAME, "")): str,
            vol.Optional(
                CONF_TECLAS, default=[str(n) for n in padrao.get(CONF_TECLAS, [])]
            ): SELETOR_TECLAS,
        }
    )


async def _monta_modulo(
    dados: dict[str, Any],
    outros: list[dict[str, Any]],
    atual: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Valida o formulario e devolve (modulo, None) ou (None, erro)."""
    host = dados[CONF_HOST].strip()
    porta = int(dados[CONF_PORT])
    if atual and host == atual[CONF_HOST] and porta == atual[CONF_PORT]:
        # so mudou nome ou teclas: nao precisa perguntar
        identidade = Identidade(
            atual[CONF_MAC], atual.get(CONF_TIPO, TIPO_RELE), atual.get(CONF_SAIDAS, N_SAIDAS)
        )
    else:
        try:
            identidade = await sonda(host, porta)
        except SemConexao:
            return None, "cannot_connect"
        except SemResposta:
            return None, "sem_resposta"
        if atual and identidade.mac != atual[CONF_MAC]:
            return None, "mac_diferente"
    mac = identidade.mac
    if any(m[CONF_MAC] == mac for m in outros):
        return None, "ja_cadastrado"
    modulo = _modulo(host, porta, identidade, dados)
    if atual and atual.get(CONF_MAC_COMPLETO):
        # visto pela descoberta: editar o nome nao pode apagar
        modulo[CONF_MAC_COMPLETO] = atual[CONF_MAC_COMPLETO]
    return modulo, None


def _modulo(host: str, porta: int, identidade: Identidade, dados: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_HOST: host,
        CONF_PORT: porta,
        CONF_MAC: identidade.mac,
        CONF_TIPO: identidade.tipo,
        CONF_SAIDAS: identidade.saidas,
        CONF_NAME: dados[CONF_NAME].strip() or f"ControlArt {identidade.mac}",
        CONF_TECLAS: sorted(int(n) for n in dados.get(CONF_TECLAS, [])),
    }


def _esquema_descoberto(nome: str) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=nome): str,
            vol.Optional(CONF_TECLAS, default=[]): SELETOR_TECLAS,
        }
    )


class ControlArtConfigFlow(ConfigFlow, domain=DOMAIN):
    """Uma entrada so, com todos os modulos dentro."""

    VERSION = 2

    # visto pela descoberta e ja perguntado: (ip, MAC inteiro, identidade)
    _descoberto: tuple[str, str, Identidade]

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return OpcoesControlArt()

    def _entrada(self) -> ConfigEntry | None:
        """A entrada unica, com todos os modulos; os 'ignorar' de cada card nao contam."""
        return next(iter(self._async_current_entries(include_ignore=False)), None)

    async def async_step_dhcp(self, discovery_info: Any) -> ConfigFlowResult:
        """Aparelho com MAC 00:60:37 visto na rede (DhcpServiceInfo: ip, macaddress)."""
        host = discovery_info.ip
        completo = mac_da_rede(discovery_info.macaddress)
        curto = completo[-8:]
        entrada = self._entrada()
        if entrada is not None:
            modulos = list(entrada.options.get(CONF_MODULOS, []))
            if any(m[CONF_MAC] == curto for m in modulos):
                novos = [
                    {**m, CONF_HOST: host, CONF_MAC_COMPLETO: completo} if m[CONF_MAC] == curto else m
                    for m in modulos
                ]
                if novos != modulos:
                    # IP novo: a entrada recarrega e o modulo volta no endereco certo
                    self.hass.config_entries.async_update_entry(
                        entrada, options={**entrada.options, CONF_MODULOS: novos}
                    )
                return self.async_abort(reason="ja_cadastrado")
        # um card por modulo: o "ignorar" do HA vale para este modulo so
        await self.async_set_unique_id(curto)
        self._abort_if_unique_id_configured()
        try:
            identidade = await sonda(host, PORTA_PADRAO)
        except (SemConexao, SemResposta):
            return self.async_abort(reason="nao_e_controlart")
        if identidade.mac != curto:
            return self.async_abort(reason="nao_e_controlart")
        self._descoberto = (host, completo, identidade)
        self.context["title_placeholders"] = {"name": f"ControlArt {completo}"}
        return await self.async_step_descoberto()

    async def async_step_descoberto(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        host, completo, identidade = self._descoberto
        entrada = self._entrada()
        modulos = list(entrada.options.get(CONF_MODULOS, [])) if entrada else []
        if user_input is not None:
            if any(m[CONF_MAC] == identidade.mac for m in modulos):
                return self.async_abort(reason="ja_cadastrado")
            modulo = {
                **_modulo(host, PORTA_PADRAO, identidade, user_input),
                CONF_MAC_COMPLETO: completo,
            }
            if entrada is not None:
                self.hass.config_entries.async_update_entry(
                    entrada, options={**entrada.options, CONF_MODULOS: modulos + [modulo]}
                )
                return self.async_abort(reason="modulo_adicionado")
            # primeiro modulo: a entrada leva o id unico de sempre, nao o MAC do card
            await self.async_set_unique_id(DOMAIN, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="ControlArt", data={}, options={CONF_MODULOS: [modulo]}
            )
        return self.async_show_form(
            step_id="descoberto",
            data_schema=_esquema_descoberto(f"ControlArt {len(modulos) + 1:02d}"),
            description_placeholders={"mac": completo, "host": host},
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        erros: dict[str, str] = {}
        if user_input is not None:
            modulo, erro = await _monta_modulo(user_input, [])
            if erro:
                erros["base"] = erro
            else:
                return self.async_create_entry(
                    title="ControlArt", data={}, options={CONF_MODULOS: [modulo]}
                )
        return self.async_show_form(
            step_id="user",
            data_schema=_esquema(user_input or {CONF_NAME: "ControlArt 01"}),
            errors=erros,
        )


class OpcoesControlArt(OptionsFlow):
    """Adicionar, editar e remover modulos."""

    def __init__(self) -> None:
        self._mac: str | None = None

    def _modulos(self) -> list[dict[str, Any]]:
        return list(self.config_entry.options.get(CONF_MODULOS, []))

    def _seletor_modulo(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_MAC): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(value=m[CONF_MAC], label=f"{m[CONF_NAME]} · {m[CONF_HOST]}")
                            for m in self._modulos()
                        ]
                    )
                )
            }
        )

    def _salva(self, modulos: list[dict[str, Any]]) -> ConfigFlowResult:
        return self.async_create_entry(data={CONF_MODULOS: modulos})

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        opcoes = ["adicionar"]
        if self._modulos():
            opcoes += ["escolher_editar", "remover"]
        return self.async_show_menu(step_id="init", menu_options=opcoes)

    async def async_step_adicionar(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        modulos = self._modulos()
        erros: dict[str, str] = {}
        if user_input is not None:
            modulo, erro = await _monta_modulo(user_input, modulos)
            if erro:
                erros["base"] = erro
            else:
                return self._salva(modulos + [modulo])
        padrao = user_input or {CONF_NAME: f"ControlArt {len(modulos) + 1:02d}"}
        return self.async_show_form(step_id="adicionar", data_schema=_esquema(padrao), errors=erros)

    async def async_step_escolher_editar(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._mac = user_input[CONF_MAC]
            return await self.async_step_editar()
        return self.async_show_form(step_id="escolher_editar", data_schema=self._seletor_modulo())

    async def async_step_editar(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        modulos = self._modulos()
        atual = next(m for m in modulos if m[CONF_MAC] == self._mac)
        erros: dict[str, str] = {}
        if user_input is not None:
            outros = [m for m in modulos if m[CONF_MAC] != self._mac]
            modulo, erro = await _monta_modulo(user_input, outros, atual)
            if erro:
                erros["base"] = erro
            else:
                return self._salva([modulo if m[CONF_MAC] == self._mac else m for m in modulos])
        return self.async_show_form(
            step_id="editar",
            data_schema=_esquema(user_input or atual),
            errors=erros,
            description_placeholders={"mac": atual[CONF_MAC]},
        )

    async def async_step_remover(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self._salva([m for m in self._modulos() if m[CONF_MAC] != user_input[CONF_MAC]])
        return self.async_show_form(step_id="remover", data_schema=self._seletor_modulo())
