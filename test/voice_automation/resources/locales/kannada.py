"""
Kannada locale for Voice AI Test Automation
"""

LANG_CODE = "kn"
LANG_NAME = "Kannada"

SCENARIOS = {
    "greeting": {
        "user_says": ["ನಮಸ್ಕಾರ", "ನೀವು ಹೇಗಿದ್ದೀರಿ", "ವಿದಾಯ"],
        "expected": [["ನಮಸ್ಕಾರ", "ಹಲೋ", "ಸ್ವಾಗತ"], ["ಚೆನ್ನಾಗಿ", "ಒಳ್ಳೆಯ", "ಆರೋಗ್ಯ"], ["ವಿದಾಯ", "ಮತ್ತೆ ಸಿಗೋಣ", "ಧನ್ಯವಾದ"]]
    },
    "support": {
        "user_says": ["ನನಗೆ ಸಹಾಯ ಬೇಕು", "ನನ್ನ ಖಾತೆ ಲಾಕ್ ಆಗಿದೆ", "ದಯವಿಟ್ಟು ರೀಸೆಟ್ ಮಾಡಿ", "ಧನ್ಯವಾದ"],
        "expected": [["ಸಹಾಯ", "help"], ["ಖಾತೆ", "ಲಾಕ್", "account"], ["ರೀಸೆಟ್", "reset"], ["ಸ್ವಾಗತ", "welcome"]]
    },
    "booking": {
        "user_says": ["ನನಗೆ ಅಪಾಯಿಂಟ್ಮೆಂಟ್ ಬೇಕು", "ನಾಳೆ ಮಧ್ಯಾಹ್ನ 3 ಗಂಟೆಗೆ", "ಹೌದು, ದೃಢೀಕರಿಸಿ"],
        "expected": [["ಅಪಾಯಿಂಟ್ಮೆಂಟ್", "appointment"], ["ನಾಳೆ", "3", "ಗಂಟೆ"], ["ದೃಢೀಕರಿಸಿ", "confirm"]]
    },
    "information": {
        "user_says": ["ನಿಮ್ಮ ಸಮಯ ಏನು", "ನೀವು ಎಲ್ಲಿ ಇದ್ದೀರಿ", "ನೀವು ಯಾವ ಸೇವೆಗಳನ್ನು ನೀಡುತ್ತೀರಿ"],
        "expected": [["ಸಮಯ", "ಗಂಟೆ", "hours"], ["ಸ್ಥಳ", "ವಿಳಾಸ", "location"], ["ಸೇವೆ", "services"]]
    }
}

# System prompts for LLM validation
SYSTEM_PROMPT = """ನೀವು ಸಹಾಯಕ ಧ್ವನಿ ಸಹಾಯಕರಾಗಿದ್ದೀರಿ. ಸಹಜವಾಗಿ ಮತ್ತು ಸಂವಾದಾತ್ಮಕವಾಗಿ ಉತ್ತರಿಸಿ."""

# Expected response patterns
RESPONSE_PATTERNS = {
    "greeting_response": r"(ನಮಸ್ಕಾರ|ಹಲೋ|ಸ್ವಾಗತ)",
    "help_response": r"(ಸಹಾಯ|ಹೇಳಿ|ಏನು)",
    "confirmation_response": r"(ಹೌದು|ಆಗಬಹುದು|ಖಂಡಿತ)",
    "farewell_response": r"(ವಿದಾಯ|ಧನ್ಯವಾದ|ಮತ್ತೆ)"
}
