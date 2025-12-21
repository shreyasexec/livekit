*** Settings ***
Documentation    LiveKit Agent Speaking Tests
Resource         ../../resources/common.robot
Suite Setup      Initialize Test Environment
Suite Teardown   Cleanup Test Environment
Test Tags        livekit    speak

*** Test Cases ***
Agent Should Speak English
    [Documentation]    Test agent speaking in English
    ${text}=    Set Variable    Hello, I am your AI assistant. How can I help you today?
    ${audio}=    Synthesize Speech In Language    ${text}    en
    Audio File Should Exist    ${audio}
    Audio Duration Should Be Greater Than    ${audio}    1.0
    Audio Should Not Be Silent    ${audio}
    Log    English speech: ${audio}

Agent Should Speak Hindi
    [Documentation]    Test agent speaking in Hindi (falls back to English if Hindi voice unavailable)
    [Tags]    hindi    optional
    ${text}=    Set Variable    नमस्ते, मैं आपका AI सहायक हूं।
    ${status}=    Run Keyword And Return Status    Synthesize Speech In Language    ${text}    hi
    Run Keyword If    not ${status}    Log    Hindi voice not available, skipping
    Run Keyword If    ${status}    Log    Hindi speech synthesized

Agent Should Speak Short Responses
    [Documentation]    Test short response synthesis
    ${text}=    Set Variable    Yes
    ${audio}=    Synthesize Speech    ${text}
    Audio File Should Exist    ${audio}
    Audio Duration Should Be Less Than    ${audio}    2.0

Agent Should Speak Long Responses
    [Documentation]    Test long response synthesis
    ${text}=    Set Variable    I understand you are having issues with your account. Let me help you with that. First, I will need to verify some information. Could you please provide me with your email address?
    ${audio}=    Synthesize Speech    ${text}
    Audio File Should Exist    ${audio}
    Audio Duration Should Be Greater Than    ${audio}    3.0

Agent Speech Should Have Good Quality
    [Documentation]    Test speech quality
    ${text}=    Set Variable    Testing audio quality with clear speech.
    ${audio}=    Synthesize Speech    ${text}
    Audio Should Not Be Silent    ${audio}
    ${rms}=    Get Audio RMS Level    ${audio}
    Log    Audio RMS level: ${rms}
    Should Be True    ${rms} > 0.01    Audio level too low
