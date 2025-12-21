*** Settings ***
Documentation    Marathi Language Tests
Resource         ../../resources/common.robot
Suite Setup      Initialize Test Environment
Test Setup       Open App And Join Room    marathi-test-room    marathi-user
Test Teardown    Run Keywords    Close App And Disconnect    AND    Cleanup Audio Files
Suite Teardown   Cleanup Test Environment
Test Tags        multilang    marathi

*** Test Cases ***
Marathi TTS Synthesis
    [Documentation]    Test Marathi TTS synthesis
    [Tags]    tts
    ${text}=    Set Variable    नमस्कार, तुम्ही कसे आहात?
    ${audio}=    Synthesize Speech In Language    ${text}    mr
    Audio File Should Exist    ${audio}
    # May fall back to Hindi/English voice if Marathi not available
    Log    Marathi audio generated: ${audio}

Marathi LLM Response
    [Documentation]    Test LLM responds to Marathi input
    [Tags]    llm
    ${response}=    Generate LLM Response    नमस्कार, तुम्ही कसे आहात?
    Response Should Not Be Empty    ${response}
    Log    Response to Marathi: ${response}

Marathi Greeting Scenario
    [Documentation]    Test greeting in Marathi
    Set Validation Language    marathi
    Sleep    3s    Wait for agent
    @{inputs}=    Get Scenario User Inputs    greeting    marathi
    Log    Marathi greeting inputs: ${inputs}

    FOR    ${input}    IN    @{inputs}
        Log    Marathi input: ${input}
        ${response}=    Generate LLM Response    ${input}
        Log    LLM Response: ${response}
    END

Marathi Conversation
    [Documentation]    Test Marathi conversation
    Set Validation Language    marathi
    Sleep    3s    Wait for agent
    @{turns}=    Create List    नमस्कार    तुम्ही कसे आहात    धन्यवाद

    FOR    ${turn}    IN    @{turns}
        Speak Via WebRTC    ${turn}    mr
        ${response}=    Listen From WebRTC    15
        Log    ${turn} -> ${response}
    END

*** Keywords ***
Close App And Disconnect
    Run Keyword And Ignore Error    Disconnect WebRTC
    Run Keyword And Ignore Error    Close Browser
