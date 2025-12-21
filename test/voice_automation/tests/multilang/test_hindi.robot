*** Settings ***
Documentation    Hindi Language Tests
Resource         ../../resources/common.robot
Suite Setup      Initialize Test Environment
Test Setup       Open App And Join Room    hindi-test-room    hindi-user
Test Teardown    Run Keywords    Close App And Disconnect    AND    Cleanup Audio Files
Suite Teardown   Cleanup Test Environment
Test Tags        multilang    hindi

*** Test Cases ***
Hindi TTS Synthesis
    [Documentation]    Test Hindi TTS synthesis
    [Tags]    tts
    ${text}=    Set Variable    नमस्ते, आप कैसे हैं?
    ${audio}=    Synthesize Speech In Language    ${text}    hi
    Audio File Should Exist    ${audio}
    Audio Should Not Be Silent    ${audio}
    Log    Hindi audio generated: ${audio}

Hindi LLM Response
    [Documentation]    Test LLM responds to Hindi input
    [Tags]    llm
    ${response}=    Generate LLM Response    नमस्ते, कैसे हो?
    Response Should Not Be Empty    ${response}
    Log    Response to Hindi: ${response}

Hindi Greeting Scenario
    [Documentation]    Test greeting in Hindi
    Set Validation Language    hindi
    Sleep    3s    Wait for agent
    @{inputs}=    Get Scenario User Inputs    greeting    hindi
    Log    Hindi greeting inputs: ${inputs}

    FOR    ${input}    IN    @{inputs}
        ${audio}=    Synthesize Speech In Language    ${input}    hi
        Log    Generated audio for: ${input}
    END

Hindi Conversation
    [Documentation]    Test Hindi conversation
    Set Validation Language    hindi
    Sleep    3s    Wait for agent
    @{turns}=    Create List    नमस्ते    आप कैसे हैं    धन्यवाद

    FOR    ${turn}    IN    @{turns}
        Speak Via WebRTC    ${turn}    hi
        ${response}=    Listen From WebRTC    15
        Log    ${turn} -> ${response}
    END

*** Keywords ***
Close App And Disconnect
    Run Keyword And Ignore Error    Disconnect WebRTC
    Run Keyword And Ignore Error    Close Browser
