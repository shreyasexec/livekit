"""
Locale modules for multi-language test support
"""
from . import english, hindi, kannada, marathi

LOCALES = {
    "english": english,
    "hindi": hindi,
    "kannada": kannada,
    "marathi": marathi
}

def get_locale(language: str):
    """Get locale module by language name"""
    return LOCALES.get(language.lower())

def get_scenarios(language: str, scenario_type: str = None):
    """Get test scenarios for a language"""
    locale = get_locale(language)
    if not locale:
        return None
    if scenario_type:
        return locale.SCENARIOS.get(scenario_type)
    return locale.SCENARIOS
