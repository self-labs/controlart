"""Base comum das entidades ControlArt: um dispositivo por modulo."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SIGNAL_CONEXAO, SIGNAL_ESTADO, TIPO_DIMMER, TIPO_RELE
from .protocolo import ModuloConexao

MODELOS = {TIPO_RELE: "Módulo Cabeado Relé", TIPO_DIMMER: "Módulo Cabeado Dimmer"}


class EntidadeControlArt(Entity):
    """Entidade ligada a um modulo. Redesenha quando o estado ou a conexao mudam."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, modulo: ModuloConexao) -> None:
        self._modulo = modulo
        # O identificador segue o MAC curto (tres ultimos bytes), como os unique_id;
        # o card mostra o inteiro, como o mdConfig. O firmware chega depois da
        # conexao e entra pelo registro (registro.atualiza_dispositivo), que
        # tambem tira o MAC curto dos dispositivos criados ate a 2026.10.3.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, modulo.mac)},
            connections={(CONNECTION_NETWORK_MAC, modulo.mac_completo)},
            name=modulo.nome,
            manufacturer="ControlArt",
            model=MODELOS[modulo.tipo],
        )

    def _sinais(self) -> tuple[str, ...]:
        return (SIGNAL_ESTADO.format(self._modulo.mac), SIGNAL_CONEXAO.format(self._modulo.mac))

    @property
    def available(self) -> bool:
        return self._modulo.conectado and self._modulo.tem_estado

    async def async_added_to_hass(self) -> None:
        for sinal in self._sinais():
            self.async_on_remove(async_dispatcher_connect(self.hass, sinal, self._atualiza))

    @callback
    def _atualiza(self) -> None:
        self.async_write_ha_state()
