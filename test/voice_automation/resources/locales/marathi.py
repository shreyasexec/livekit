"""
Marathi locale for Voice AI Test Automation
"""

LANG_CODE = "mr"
LANG_NAME = "Marathi"

SCENARIOS = {
    "greeting": {
        "user_says": ["नमस्कार", "तुम्ही कसे आहात", "निरोप"],
        "expected": [["नमस्कार", "हॅलो", "स्वागत"], ["चांगले", "ठीक", "बरे"], ["निरोप", "भेटू", "धन्यवाद"]]
    },
    "support": {
        "user_says": ["मला मदत हवी आहे", "माझे खाते लॉक आहे", "कृपया रीसेट करा", "धन्यवाद"],
        "expected": [["मदत", "सहाय्य", "help"], ["खाते", "लॉक", "account"], ["रीसेट", "reset"], ["स्वागत", "welcome"]]
    },
    "booking": {
        "user_says": ["मला अपॉइंटमेंट बुक करायची आहे", "उद्या दुपारी 3 वाजता", "हो, पुष्टी करा"],
        "expected": [["अपॉइंटमेंट", "बुक", "appointment"], ["उद्या", "3", "वाजता"], ["पुष्टी", "confirm"]]
    },
    "information": {
        "user_says": ["तुमची वेळ काय आहे", "तुम्ही कुठे आहात", "तुम्ही कोणत्या सेवा देता"],
        "expected": [["वेळ", "तास", "hours"], ["ठिकाण", "पत्ता", "location"], ["सेवा", "services"]]
    }
}

# System prompts for LLM validation
SYSTEM_PROMPT = """तुम्ही एक मदतगार व्हॉइस असिस्टंट आहात. नैसर्गिक आणि संवादात्मक पद्धतीने उत्तर द्या."""

# Expected response patterns
RESPONSE_PATTERNS = {
    "greeting_response": r"(नमस्कार|हॅलो|स्वागत)",
    "help_response": r"(मदत|सांगा|काय)",
    "confirmation_response": r"(हो|नक्की|अवश्य)",
    "farewell_response": r"(निरोप|धन्यवाद|भेटू)"
}
