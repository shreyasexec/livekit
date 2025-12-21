"""
Configuration file for Robot Framework tests
This file is loaded before any tests run
"""
# Apply nest_asyncio FIRST before any other imports
try:
    import nest_asyncio
    nest_asyncio.apply()
except ImportError:
    pass

# This allows the Playwright sync API to work within Robot Framework
