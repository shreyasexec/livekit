"""
Hindi locale for Voice AI Test Automation
"""

LANG_CODE = "hi"
LANG_NAME = "Hindi"

SCENARIOS = {
    "greeting": {
        "user_says": ["नमस्ते", "आप कैसे हैं", "अलविदा"],
        "expected": [["नमस्ते", "हैलो", "नमस्कार"], ["अच्छा", "ठीक", "बढ़िया"], ["अलविदा", "फिर मिलेंगे", "धन्यवाद"]]
    },
    "support": {
        "user_says": ["मुझे मदद चाहिए", "मेरा अकाउंट लॉक है", "कृपया रीसेट करें", "धन्यवाद"],
        "expected": [["मदद", "सहायता", "help"], ["अकाउंट", "लॉक", "account"], ["रीसेट", "हो गया", "reset"], ["स्वागत", "welcome"]]
    },
    "booking": {
        "user_says": ["मुझे अपॉइंटमेंट बुक करनी है", "कल दोपहर 3 बजे", "हाँ, कन्फर्म करें"],
        "expected": [["अपॉइंटमेंट", "बुक", "appointment"], ["कल", "3", "दोपहर"], ["कन्फर्म", "बुक", "confirm"]]
    },
    "information": {
        "user_says": ["आपका समय क्या है", "आप कहाँ स्थित हैं", "आप क्या सेवाएं देते हैं"],
        "expected": [["समय", "घंटे", "hours"], ["स्थित", "पता", "location"], ["सेवाएं", "services"]]
    }
}

# System prompts for LLM validation
SYSTEM_PROMPT = """आप एक मददगार वॉइस असिस्टेंट हैं। स्वाभाविक और बातचीत के अंदाज में जवाब दें।"""

# Expected response patterns
RESPONSE_PATTERNS = {
    "greeting_response": r"(नमस्ते|नमस्कार|हैलो|स्वागत)",
    "help_response": r"(मदद|सहायता|बताइए|क्या)",
    "confirmation_response": r"(हाँ|जी|ज़रूर|बिल्कुल)",
    "farewell_response": r"(अलविदा|फिर मिलेंगे|धन्यवाद|शुभ)"
}
