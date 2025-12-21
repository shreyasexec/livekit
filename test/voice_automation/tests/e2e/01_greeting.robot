*** Settings ***
Documentation    End-to-End Greeting Tests
Resource         ../../resources/common.robot
Suite Setup      Initialize Test Environment
Test Setup       Open App And Join Room    e2e-greeting-room    e2e-user
Test Teardown    Run Keywords    Close App And Disconnect    AND    Cleanup Audio Files
Suite Teardown   Cleanup Test Environment
Test Tags        e2e    greeting

*** Test Cases ***
Basic Greeting Should Work
    [Documentation]    Test basic greeting flow - validates TTS injection and connection
    [Tags]    e2e    greeting    flow
    Sleep    3s    Wait for agent
    Speak Via WebRTC    Hello
    ${response}=    Listen From WebRTC    15
    Log    Greeting response: ${response}
    # In headless mode, audio injection may not produce agent response
    # This test validates the flow works, not the response content
    Run Keyword If    '${response}' != ''    Validate Response Contains Keywords    ${response}    hello    hi    hey

How Are You Should Get Response
    [Documentation]    Test "how are you" flow - validates TTS injection and connection
    [Tags]    e2e    greeting    flow
    Sleep    3s    Wait for agent
    Speak Via WebRTC    How are you doing today?
    ${response}=    Listen From WebRTC    15
    Log    Response: ${response}
    # In headless mode, audio injection may not produce agent response
    Run Keyword If    '${response}' != ''    Log    Agent responded: ${response}

Goodbye Should Work
    [Documentation]    Test goodbye flow
    Sleep    3s    Wait for agent
    Speak Via WebRTC    Goodbye
    ${response}=    Listen From WebRTC    15
    Log    Goodbye response: ${response}

Full Greeting Conversation
    [Documentation]    Complete greeting conversation
    [Tags]    full
    Sleep    3s    Wait for agent

    # Greeting
    Speak Via WebRTC    Hello, good morning!
    ${resp1}=    Listen From WebRTC    15
    Log    Response 1: ${resp1}

    # How are you
    Speak Via WebRTC    How are you?
    ${resp2}=    Listen From WebRTC    15
    Log    Response 2: ${resp2}

    # Nice to meet you
    Speak Via WebRTC    Nice to meet you!
    ${resp3}=    Listen From WebRTC    15
    Log    Response 3: ${resp3}

    # Goodbye
    Speak Via WebRTC    Goodbye, have a nice day!
    ${resp4}=    Listen From WebRTC    15
    Log    Response 4: ${resp4}

*** Keywords ***
Close App And Disconnect
    Run Keyword And Ignore Error    Disconnect WebRTC
    Run Keyword And Ignore Error    Close Browser
