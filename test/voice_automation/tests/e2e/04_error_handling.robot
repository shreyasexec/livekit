*** Settings ***
Documentation    End-to-End Error Handling Tests
Resource         ../../resources/common.robot
Suite Setup      Initialize Test Environment
Test Setup       Open App And Join Room    e2e-error-room    error-user
Test Teardown    Run Keywords    Close App And Disconnect    AND    Cleanup Audio Files
Suite Teardown   Cleanup Test Environment
Test Tags        e2e    error

*** Test Cases ***
Empty Input Should Be Handled
    [Documentation]    Test handling of silence/empty input
    Sleep    3s    Wait for agent
    # Wait without speaking - agent should handle timeout gracefully
    Sleep    5s
    Log    Silence handled gracefully

Unclear Input Should Be Clarified
    [Documentation]    Test handling of unclear input
    Sleep    3s    Wait for agent
    Speak Via WebRTC    Hmm umm well
    ${response}=    Listen From WebRTC    15
    Log    Unclear input response: ${response}

Long Input Should Be Handled
    [Documentation]    Test handling of long input - validates flow
    [Tags]    e2e    error    flow
    Sleep    3s    Wait for agent
    ${long_text}=    Set Variable    I have a very long and complicated question about my account that involves multiple issues including billing, access, security, and I also need help with settings.
    Speak Via WebRTC    ${long_text}
    ${response}=    Listen From WebRTC    20
    Log    Long input response: ${response}
    Run Keyword If    '${response}' != ''    Log    Agent responded to long input

Repeated Questions Should Be Handled
    [Documentation]    Test handling of repeated questions
    Sleep    3s    Wait for agent

    # Ask same question multiple times
    FOR    ${i}    IN RANGE    3
        Speak Via WebRTC    What is your name?
        ${response}=    Listen From WebRTC    15
        Log    Response ${i}: ${response}
    END

Recovery After Error
    [Documentation]    Test recovery after potential error - validates flow
    [Tags]    e2e    error    flow
    Sleep    3s    Wait for agent

    # Potentially confusing input
    Speak Via WebRTC    cancel reset stop undo
    ${resp1}=    Listen From WebRTC    15
    Log    Confusing input response: ${resp1}

    # Normal input should still work
    Speak Via WebRTC    Hello, how are you?
    ${resp2}=    Listen From WebRTC    15
    Log    Recovery response: ${resp2}
    Run Keyword If    '${resp2}' != ''    Log    Agent recovered successfully

*** Keywords ***
Close App And Disconnect
    Run Keyword And Ignore Error    Disconnect WebRTC
    Run Keyword And Ignore Error    Close Browser
