"""Endereco IP de cada modulo, como sensor de diagnostico.

Aparece na pagina do dispositivo, para achar o modulo na rede sem abrir a
configuracao da integracao. Continua disponivel com o modulo fora do ar,
que e justamente quando mais se precisa dele.
"""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entidade import EntidadeControlArt
from .protocolo import ControlArtHub, ModuloConexao


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    hub: ControlArtHub = entry.runtime_data
    async_add_entities(EnderecoIP(modulo) for modulo in hub.modulos.values())


class EnderecoIP(EntidadeControlArt, SensorEntity):
    """O IP cadastrado. Muda so quando o modulo e editado nas opcoes."""

    _attr_translation_key = "ip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:ip-network"

    def __init__(self, modulo: ModuloConexao) -> None:
        super().__init__(modulo)
        self._attr_unique_id = f"controlart_{modulo.mac}_ip"

    def _sinais(self) -> tuple[str, ...]:
        return ()                       # o valor vem do cadastro, nao do modulo

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> str:
        return self._modulo.host
