*** Settings ***
Documentation    Language Switching Tests
Resource         ../../resources/common.robot
Suite Setup      Initialize Test Environment
Test Setup       Open App And Join Room    multilang-test    multilang-user
Test Teardown    Run Keywords    Close App And Disconnect    AND    Cleanup Audio Files
Suite Teardown   Cleanup Test Environment
Test Tags        multilang    switch

*** Test Cases ***
Switch From English To Hindi
    [Documentation]    Test switching from English to Hindi
    Sleep    3s    Wait for agent

    # Start in English
    Speak Via WebRTC    Hello, how are you?    english
    ${english_response}=    Listen From WebRTC    15
    Log    English response: ${english_response}

    # Switch to Hindi
    Speak Via WebRTC    नमस्ते, कैसे हो?    hi
    ${hindi_response}=    Listen From WebRTC    15
    Log    Hindi response: ${hindi_response}

Switch Through All Languages
    [Documentation]    Test switching through all supported languages
    Sleep    3s    Wait for agent

    # English
    Speak Via WebRTC    Hello    english
    ${en_resp}=    Listen From WebRTC    15
    Log    English: ${en_resp}

    # Hindi
    Speak Via WebRTC    नमस्ते    hi
    ${hi_resp}=    Listen From WebRTC    15
    Log    Hindi: ${hi_resp}

    # Kannada
    Speak Via WebRTC    ನಮಸ್ಕಾರ    kn
    ${kn_resp}=    Listen From WebRTC    15
    Log    Kannada: ${kn_resp}

    # Marathi
    Speak Via WebRTC    नमस्कार    mr
    ${mr_resp}=    Listen From WebRTC    15
    Log    Marathi: ${mr_resp}

    # Back to English
    Speak Via WebRTC    Goodbye    english
    ${bye_resp}=    Listen From WebRTC    15
    Log    Final English: ${bye_resp}

Language Codes Should Be Correct
    [Documentation]    Verify language codes
    ${en_code}=    Get Language Code    english
    ${hi_code}=    Get Language Code    hindi
    ${kn_code}=    Get Language Code    kannada
    ${mr_code}=    Get Language Code    marathi

    Should Be Equal    ${en_code}    en
    Should Be Equal    ${hi_code}    hi
    Should Be Equal    ${kn_code}    kn
    Should Be Equal    ${mr_code}    mr

All Languages Should Have Scenarios
    [Documentation]    Verify all languages have test scenarios
    @{languages}=    Get Available Languages

    FOR    ${lang}    IN    @{languages}
        @{scenarios}=    Get Available Scenarios    ${lang}
        Log    ${lang} scenarios: ${scenarios}
        Should Not Be Empty    ${scenarios}    ${lang} should have scenarios
    END

*** Keywords ***
Close App And Disconnect
    Run Keyword And Ignore Error    Disconnect WebRTC
    Run Keyword And Ignore Error    Close Browser
