"""Botoes "Acender tudo" e "Apagar tudo" de cada modulo.

Um comando so para o modulo inteiro, em vez de um por saida: mais rapido e
sem o efeito de cascata das luzes apagando uma a uma. Vale so para o modulo
do botao; os outros nao sao tocados.
"""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entidade import EntidadeControlArt
from .protocolo import ControlArtHub, ModuloConexao


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    hub: ControlArtHub = entry.runtime_data
    async_add_entities(
        botao(modulo) for modulo in hub.modulos.values() for botao in (AcenderTudo, ApagarTudo)
    )


class _Tudo(EntidadeControlArt, ButtonEntity):
    _ligado: bool

    def __init__(self, modulo: ModuloConexao) -> None:
        super().__init__(modulo)
        self._attr_unique_id = f"controlart_{modulo.mac}_{self._attr_translation_key}"

    @property
    def available(self) -> bool:
        return self._modulo.conectado

    async def async_press(self) -> None:
        await self._modulo.envia_todos(self._ligado)


class AcenderTudo(_Tudo):
    _attr_translation_key = "acender_tudo"
    _attr_icon = "mdi:lightbulb-group"
    _ligado = True


class ApagarTudo(_Tudo):
    _attr_translation_key = "apagar_tudo"
    _attr_icon = "mdi:lightbulb-group-off"
    _ligado = False
