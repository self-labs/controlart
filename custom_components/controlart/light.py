"""As saidas de cada modulo como luzes.

O rele e liga/desliga, entao suas 10 saidas entram como `light` com
ColorMode.ONOFF. Os canais do dimmer entram com brilho: o nivel do modulo
(0 a 255) e o proprio brilho do Home Assistant, na mesma escala. Isso permite
"apagar as luzes da cozinha" por area, voz e cartoes de luz.

O estado vem sempre do modulo: apos o comando esperamos o quadro de
confirmacao, que chega em milissegundos. Sem estado otimista.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import TIPO_DIMMER
from .entidade import EntidadeControlArt
from .protocolo import ControlArtHub, ModuloConexao


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    hub: ControlArtHub = entry.runtime_data
    async_add_entities(
        (CanalDimmer if modulo.tipo == TIPO_DIMMER else Saida)(modulo, canal)
        for modulo in hub.modulos.values()
        for canal in range(1, modulo.n_saidas + 1)
    )


class Saida(EntidadeControlArt, LightEntity):
    """Um circuito."""

    _attr_translation_key = "saida"
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, modulo: ModuloConexao, canal: int) -> None:
        super().__init__(modulo)
        self._canal = canal
        self._attr_translation_placeholders = {"numero": str(canal)}
        self._attr_unique_id = f"controlart_{modulo.mac}_luz_{canal:02d}"

    @property
    def is_on(self) -> bool:
        return bool(self._modulo.saidas[self._canal - 1])

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._modulo.envia_rele(self._canal, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._modulo.envia_rele(self._canal, False)


class CanalDimmer(Saida):
    """Um canal do dimmer. Sem brilho pedido, acende no ultimo nivel visto.

    Com `transition`, a rampa roda em segundo plano (ver ModuloConexao.rampa):
    o servico volta na hora, e o brilho acompanha os quadros do modulo.
    """

    _attr_translation_key = "canal"
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_supported_features = LightEntityFeature.TRANSITION

    @property
    def brightness(self) -> int:
        return self._modulo.saidas[self._canal - 1]

    async def async_turn_on(self, **kwargs: Any) -> None:
        nivel = kwargs.get(ATTR_BRIGHTNESS)
        if nivel is None:
            nivel = self._modulo.nivel_ao_ligar(self._canal)
        await self._ajusta(nivel, kwargs.get(ATTR_TRANSITION))

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._ajusta(0, kwargs.get(ATTR_TRANSITION))

    async def _ajusta(self, nivel: int, segundos: float | None) -> None:
        if segundos:
            self._modulo.rampa(self._canal, nivel, segundos)
        else:
            await self._modulo.envia_nivel(self._canal, nivel)
