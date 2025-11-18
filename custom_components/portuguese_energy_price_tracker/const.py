"""Constants for the Energy Price Tracker integration."""
from typing import Final

DOMAIN: Final = "energy_price_tracker"

# Configuration
CONF_PROVIDER: Final = "provider"
CONF_TARIFF: Final = "tariff"
CONF_DISPLAY_NAME: Final = "display_name"
CONF_VAT: Final = "vat"
CONF_INCLUDE_VAT: Final = "include_vat"

# Defaults
DEFAULT_SCAN_INTERVAL: Final = 300  # 5 minutes
SCAN_INTERVAL: Final = DEFAULT_SCAN_INTERVAL
DEFAULT_VAT: Final = 23
DEFAULT_INCLUDE_VAT: Final = True

# Supported providers and their tariffs (from GitHub CSV)
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
    "Coopérnico Base": {
        "name": "Coopérnico Base",
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
    "Coopérnico GO": {
        "name": "Coopérnico GO",
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
    "EZU Tarifa Coletiva": {
        "name": "EZU Tarifa Coletiva",
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
    "G9 Smart Dynamic": {
        "name": "G9 Smart Dynamic",
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
    "MeoEnergia Tarifa Variável": {
        "name": "MeoEnergia Tarifa Variável",
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
