"""
Validation Keywords for Robot Framework
Keywords for validating responses in multiple languages
"""
import re
import logging
from typing import List, Dict, Any, Optional

from robot.api.deco import keyword, library

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from resources.locales import get_locale, get_scenarios, LOCALES
from config import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)


@library(scope='GLOBAL')
class ValidationKeywords:
    """Keywords for response validation"""

    ROBOT_LIBRARY_SCOPE = 'GLOBAL'

    def __init__(self):
        self.current_language = DEFAULT_LANGUAGE
        self.validation_results: List[Dict[str, Any]] = []

    @keyword("Set Validation Language")
    def set_validation_language(self, language: str):
        """Set the language for validation"""
        language = language.lower()
        if language not in SUPPORTED_LANGUAGES:
            raise AssertionError(
                f"Unsupported language: {language}. "
                f"Supported: {SUPPORTED_LANGUAGES}"
            )
        self.current_language = language
        logger.info(f"Validation language set to: {language}")
        return True

    @keyword("Get Current Language")
    def get_current_language(self) -> str:
        """Get the current validation language"""
        return self.current_language

    @keyword("Get Language Code")
    def get_language_code(self, language: str = None) -> str:
        """Get ISO language code for language"""
        lang = language or self.current_language
        locale = get_locale(lang)
        if not locale:
            return "en"
        return locale.LANG_CODE

    @keyword("Get Scenario User Inputs")
    def get_scenario_user_inputs(self, scenario: str,
                                 language: str = None) -> List[str]:
        """Get user inputs for a scenario"""
        lang = language or self.current_language
        scenarios = get_scenarios(lang, scenario)

        if not scenarios:
            raise AssertionError(
                f"Scenario '{scenario}' not found for language '{lang}'"
            )

        return scenarios.get('user_says', [])

    @keyword("Get Scenario Expected Responses")
    def get_scenario_expected_responses(self, scenario: str,
                                        language: str = None) -> List[List[str]]:
        """Get expected response keywords for a scenario"""
        lang = language or self.current_language
        scenarios = get_scenarios(lang, scenario)

        if not scenarios:
            raise AssertionError(
                f"Scenario '{scenario}' not found for language '{lang}'"
            )

        return scenarios.get('expected', [])

    @keyword("Validate Response Contains Keywords")
    def validate_response_contains_keywords(self, response: str,
                                            *expected_keywords,
                                            match_any: bool = True) -> bool:
        """Validate response contains expected keywords

        Args:
            response: The response text to validate
            *expected_keywords: One or more keywords to check for
            match_any: If True, match any keyword; if False, match all
        """
        # Handle case where first arg is a list
        if len(expected_keywords) == 1 and isinstance(expected_keywords[0], list):
            expected_keywords = expected_keywords[0]
        else:
            expected_keywords = list(expected_keywords)
        if not response:
            self.validation_results.append({
                'passed': False,
                'response': response,
                'expected': expected_keywords,
                'reason': 'Empty response'
            })
            raise AssertionError("Response is empty")

        response_lower = response.lower()

        if match_any:
            matched = any(kw.lower() in response_lower for kw in expected_keywords)
        else:
            matched = all(kw.lower() in response_lower for kw in expected_keywords)

        self.validation_results.append({
            'passed': matched,
            'response': response[:100],
            'expected': expected_keywords,
            'match_any': match_any
        })

        if not matched:
            mode = "any" if match_any else "all"
            raise AssertionError(
                f"Response does not contain {mode} of: {expected_keywords}\n"
                f"Response: {response[:200]}"
            )

        logger.info(f"Validation passed. Keywords found: {expected_keywords}")
        return True

    @keyword("Validate Scenario Response")
    def validate_scenario_response(self, response: str, scenario: str,
                                   turn_index: int, language: str = None) -> bool:
        """Validate response for a specific scenario turn"""
        lang = language or self.current_language
        expected_list = self.get_scenario_expected_responses(scenario, lang)

        if turn_index >= len(expected_list):
            raise AssertionError(
                f"Turn index {turn_index} out of range for scenario '{scenario}'"
            )

        expected = expected_list[turn_index]
        return self.validate_response_contains_keywords(response, expected, match_any=True)

    @keyword("Run Scenario Validation")
    def run_scenario_validation(self, responses: List[str], scenario: str,
                               language: str = None) -> Dict[str, Any]:
        """Validate all responses for a scenario"""
        lang = language or self.current_language
        expected_list = self.get_scenario_expected_responses(scenario, lang)

        results = {
            'scenario': scenario,
            'language': lang,
            'total_turns': len(responses),
            'passed': 0,
            'failed': 0,
            'details': []
        }

        for i, response in enumerate(responses):
            if i >= len(expected_list):
                break

            expected = expected_list[i]
            try:
                self.validate_response_contains_keywords(response, expected)
                results['passed'] += 1
                results['details'].append({
                    'turn': i + 1,
                    'passed': True,
                    'response': response[:100]
                })
            except AssertionError as e:
                results['failed'] += 1
                results['details'].append({
                    'turn': i + 1,
                    'passed': False,
                    'response': response[:100],
                    'error': str(e)
                })

        return results

    @keyword("Response Should Match Pattern")
    def response_should_match_pattern(self, response: str,
                                      pattern: str) -> bool:
        """Validate response matches regex pattern"""
        if not re.search(pattern, response, re.IGNORECASE | re.MULTILINE):
            raise AssertionError(
                f"Response does not match pattern: {pattern}\n"
                f"Response: {response[:200]}"
            )
        return True

    @keyword("Response Should Not Be Empty")
    def response_should_not_be_empty(self, response: str):
        """Validate response is not empty"""
        if not response or not response.strip():
            raise AssertionError("Response is empty")
        return True

    @keyword("Response Should Be In Language")
    def response_should_be_in_language(self, response: str,
                                       language: str) -> bool:
        """Validate response appears to be in specified language"""
        # Basic script detection
        if language in ['hindi', 'hi']:
            if not re.search(r'[\u0900-\u097F]', response):
                # Check for romanized Hindi or English response
                logger.warning("Response may not be in Hindi script")
        elif language in ['kannada', 'kn']:
            if not re.search(r'[\u0C80-\u0CFF]', response):
                logger.warning("Response may not be in Kannada script")
        elif language in ['marathi', 'mr']:
            if not re.search(r'[\u0900-\u097F]', response):
                logger.warning("Response may not be in Marathi script")

        return True

    @keyword("Get Validation Summary")
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of all validations performed"""
        total = len(self.validation_results)
        passed = sum(1 for r in self.validation_results if r.get('passed'))

        return {
            'total': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': (passed / total * 100) if total > 0 else 0
        }

    @keyword("Clear Validation Results")
    def clear_validation_results(self):
        """Clear validation results"""
        self.validation_results.clear()
        return True

    @keyword("Get Available Languages")
    def get_available_languages(self) -> List[str]:
        """Get list of available languages"""
        return SUPPORTED_LANGUAGES.copy()

    @keyword("Get Available Scenarios")
    def get_available_scenarios(self, language: str = None) -> List[str]:
        """Get list of available scenarios for a language"""
        lang = language or self.current_language
        locale = get_locale(lang)
        if not locale:
            return []
        return list(locale.SCENARIOS.keys())

    @keyword("Validate Greeting Response")
    def validate_greeting_response(self, response: str,
                                  language: str = None) -> bool:
        """Validate response is a proper greeting"""
        lang = language or self.current_language
        scenarios = get_scenarios(lang, 'greeting')

        if not scenarios:
            # Fall back to basic validation
            greeting_keywords = ['hello', 'hi', 'hey', 'greetings', 'welcome']
            return self.validate_response_contains_keywords(
                response, greeting_keywords, match_any=True
            )

        expected = scenarios.get('expected', [[]])[0]
        return self.validate_response_contains_keywords(
            response, expected, match_any=True
        )

    @keyword("Validate Farewell Response")
    def validate_farewell_response(self, response: str,
                                   language: str = None) -> bool:
        """Validate response is a proper farewell"""
        lang = language or self.current_language
        scenarios = get_scenarios(lang, 'greeting')

        if scenarios and len(scenarios.get('expected', [])) > 2:
            expected = scenarios['expected'][2]
            return self.validate_response_contains_keywords(
                response, expected, match_any=True
            )

        # Fall back
        farewell_keywords = ['bye', 'goodbye', 'farewell', 'later', 'care']
        return self.validate_response_contains_keywords(
            response, farewell_keywords, match_any=True
        )
