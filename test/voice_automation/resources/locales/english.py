"""
English locale for Voice AI Test Automation
"""

LANG_CODE = "en"
LANG_NAME = "English"

SCENARIOS = {
    "greeting": {
        "user_says": ["Hello", "How are you", "Goodbye"],
        "expected": [["hello", "hi", "hey"], ["good", "fine", "well", "great"], ["bye", "goodbye", "later"]]
    },
    "support": {
        "user_says": ["I need help", "My account is locked", "Please reset it", "Thank you"],
        "expected": [["help", "assist"], ["account", "locked"], ["reset", "done", "will"], ["welcome", "pleasure"]]
    },
    "booking": {
        "user_says": ["I want to book an appointment", "Tomorrow at 3 PM", "Yes, confirm it"],
        "expected": [["appointment", "book", "schedule"], ["tomorrow", "3", "time"], ["confirm", "booked", "scheduled"]]
    },
    "information": {
        "user_says": ["What are your hours", "Where are you located", "What services do you offer"],
        "expected": [["hours", "open", "available"], ["location", "address", "located"], ["services", "offer", "provide"]]
    }
}

# System prompts for LLM validation
SYSTEM_PROMPT = """You are a helpful voice assistant. Respond naturally and conversationally."""

# Expected response patterns
RESPONSE_PATTERNS = {
    "greeting_response": r"(?i)(hello|hi|hey|greetings|good\s+(morning|afternoon|evening))",
    "help_response": r"(?i)(help|assist|support|what.*can.*do)",
    "confirmation_response": r"(?i)(yes|sure|certainly|of course|no problem)",
    "farewell_response": r"(?i)(goodbye|bye|take care|have a (nice|good))"
}
