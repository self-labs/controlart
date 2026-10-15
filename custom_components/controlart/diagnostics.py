"""Diagnostico para download (Configuracoes -> Dispositivos -> ControlArt -> Baixar diagnostico).

Serve para suporte a distancia: mostra o que cada modulo disse por ultimo,
sem precisar de terminal na rede da instalacao. Nao ha segredo a esconder:
IP e MAC sao a identificacao do modulo na rede local.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    return {"modulos": [modulo.diagnostico() for modulo in entry.runtime_data.modulos.values()]}
