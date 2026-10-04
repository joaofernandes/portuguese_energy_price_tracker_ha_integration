"""Constants for the Energy Price Tracker integration."""
from typing import Final

DOMAIN: Final = "portuguese_energy_price_tracker"

# Configuration
CONF_PROVIDER: Final = "provider"
CONF_TARIFF: Final = "tariff"
CONF_DISPLAY_NAME: Final = "display_name"
CONF_VAT: Final = "vat"
CONF_INCLUDE_VAT: Final = "include_vat"
CONF_ENABLE_DEBUG: Final = "enable_debug"

# Provider lifecycle status
PROVIDER_STATUS_SUPPORTED: Final = "supported"
PROVIDER_STATUS_LEGACY: Final = "legacy"

# Defaults
# Price data is published in 15-minute periods. The coordinator is scheduled
# on these wall-clock boundaries rather than relative to integration startup.
DEFAULT_SCAN_INTERVAL: Final = 900  # 15 minutes
SCAN_INTERVAL: Final = DEFAULT_SCAN_INTERVAL
DEFAULT_VAT: Final = 23
DEFAULT_INCLUDE_VAT: Final = True
DEFAULT_ENABLE_DEBUG: Final = False

# Supported providers and their tariffs (from the CSV source)
PROVIDERS: Final = {
    "Alfa Power Index BTN": {
        "name": "Alfa Power Index BTN",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "Coopérnico Único": {
        "name": "Coopérnico Único",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "EDP Indexada Horária": {
        "name": "EDP Indexada Horária",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "EZU Tarifa Indexada": {
        "name": "EZU Tarifa Indexada",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "G9 Smart Dynamic SPOT 8!": {
        "name": "G9 Smart Dynamic SPOT 8!",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "Galp Plano Dinâmico": {
        "name": "Galp Plano Dinâmico",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "Iberdrola - Simples Indexado Dinâmico": {
        "name": "Iberdrola - Simples Indexado Dinâmico",
        "tariffs": [
            "SIMPLE",
        ],
    },
    "MeoEnergia Tarifa Dinâmica": {
        "name": "MeoEnergia Tarifa Dinâmica",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
    "Plenitude - Tendência": {
        "name": "Plenitude - Tendência",
        "tariffs": [
            "SIMPLE",
        ],
    },
    "Repsol Leve Sem Mais": {
        "name": "Repsol Leve Sem Mais",
        "tariffs": [
            "SIMPLE",
            "BIHORARIO_DIARIO",
            "BIHORARIO_SEMANAL",
            "TRIHORARIO_DIARIO",
            "TRIHORARIO_DIARIO_HV",
            "TRIHORARIO_SEMANAL",
            "TRIHORARIO_SEMANAL_HV",
        ],
    },
}

# Tariff display names (internal codes)
TARIFF_NAMES: Final = {
    "SIMPLE": "Simples",
    "BIHORARIO_DIARIO": "Bi-horário - Ciclo Diário",
    "BIHORARIO_SEMANAL": "Bi-horário - Ciclo Semanal",
    "TRIHORARIO_DIARIO": "Tri-horário - Ciclo Diário",
    "TRIHORARIO_DIARIO_HV": "Tri-horário > 20.7 kVA - Ciclo Diário",
    "TRIHORARIO_SEMANAL": "Tri-horário - Ciclo Semanal",
    "TRIHORARIO_SEMANAL_HV": "Tri-horário > 20.7 kVA - Ciclo Semanal",
}


def get_provider_status(provider: str) -> str:
    """Return the lifecycle status for a provider in the current catalog."""
    if provider in PROVIDERS:
        return PROVIDER_STATUS_SUPPORTED
    return PROVIDER_STATUS_LEGACY
