*** Settings ***
Documentation    Kannada Language Tests
Resource         ../../resources/common.robot
Suite Setup      Initialize Test Environment
Test Setup       Open App And Join Room    kannada-test-room    kannada-user
Test Teardown    Run Keywords    Close App And Disconnect    AND    Cleanup Audio Files
Suite Teardown   Cleanup Test Environment
Test Tags        multilang    kannada

*** Test Cases ***
Kannada TTS Synthesis
    [Documentation]    Test Kannada TTS synthesis
    [Tags]    tts
    ${text}=    Set Variable    ನಮಸ್ಕಾರ, ನೀವು ಹೇಗಿದ್ದೀರಿ?
    ${audio}=    Synthesize Speech In Language    ${text}    kn
    Audio File Should Exist    ${audio}
    # May fall back to English voice if Kannada not available
    Log    Kannada audio generated: ${audio}

Kannada LLM Response
    [Documentation]    Test LLM responds to Kannada input
    [Tags]    llm
    ${response}=    Generate LLM Response    ನಮಸ್ಕಾರ, ನೀವು ಹೇಗಿದ್ದೀರಿ?
    Response Should Not Be Empty    ${response}
    Log    Response to Kannada: ${response}

Kannada Greeting Scenario
    [Documentation]    Test greeting in Kannada
    Set Validation Language    kannada
    Sleep    3s    Wait for agent
    @{inputs}=    Get Scenario User Inputs    greeting    kannada
    Log    Kannada greeting inputs: ${inputs}

    FOR    ${input}    IN    @{inputs}
        Log    Kannada input: ${input}
        ${response}=    Generate LLM Response    ${input}
        Log    LLM Response: ${response}
    END

Kannada Conversation
    [Documentation]    Test Kannada conversation
    Set Validation Language    kannada
    Sleep    3s    Wait for agent
    @{turns}=    Create List    ನಮಸ್ಕಾರ    ನೀವು ಹೇಗಿದ್ದೀರಿ    ಧನ್ಯವಾದ

    FOR    ${turn}    IN    @{turns}
        Speak Via WebRTC    ${turn}    kn
        ${response}=    Listen From WebRTC    15
        Log    ${turn} -> ${response}
    END

*** Keywords ***
Close App And Disconnect
    Run Keyword And Ignore Error    Disconnect WebRTC
    Run Keyword And Ignore Error    Close Browser
