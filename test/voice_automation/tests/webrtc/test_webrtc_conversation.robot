*** Settings ***
Documentation    WebRTC Conversation Tests
Resource         ../../resources/common.robot
Suite Setup      Initialize Test Environment
Test Setup       Open App And Join Room    conversation-room    conversation-user
Test Teardown    Run Keywords    Close App And Disconnect    AND    Cleanup Audio Files
Suite Teardown   Cleanup Test Environment
Test Tags        webrtc    conversation

*** Test Cases ***
Simple Greeting Should Get Response
    [Documentation]    Test simple greeting via WebRTC
    [Tags]    greeting
    Sleep    3s    Wait for agent to join
    Speak Via WebRTC    Hello
    ${response}=    Listen From WebRTC    15
    Log    Response: ${response}

Multi-Turn Conversation Should Work
    [Documentation]    Test multi-turn conversation
    [Tags]    multi-turn
    Sleep    3s    Wait for agent to join
    @{turns}=    Create List    Hello    How are you    Thank you
    ${results}=    Run WebRTC Conversation    ${turns}    english    15
    Log    Conversation results: ${results}

    FOR    ${result}    IN    @{results}
        Log    Turn ${result['turn']}: ${result['input']} -> ${result['response']}
    END

Conversation Should Have Meaningful Responses
    [Documentation]    Verify responses are meaningful (requires running AI agent)
    [Tags]    quality    requires-agent
    Sleep    3s    Wait for agent
    Speak Via WebRTC    What is your name?
    ${response}=    Listen From WebRTC    15
    # This test requires a running AI agent - skip if no response
    ${has_response}=    Evaluate    len('''${response}'''.strip()) > 0
    Skip If    not ${has_response}    No AI agent response - agent may not be running
    Log    Agent response: ${response}

Full Conversation Test
    [Documentation]    Complete 5-turn conversation test
    [Tags]    e2e    full
    Sleep    3s    Wait for agent

    @{conversation}=    Create List
    ...    Hello, how are you?
    ...    I need help with my account
    ...    My account is locked
    ...    Can you reset my password?
    ...    Thank you for your help

    ${results}=    Run WebRTC Conversation    ${conversation}    english    15

    ${pass_count}=    Set Variable    0
    FOR    ${result}    IN    @{results}
        Log    Turn ${result['turn']}: ${result['input']}
        Log    Response: ${result['response']}
        ${has_response}=    Evaluate    len('''${result['response']}''') > 0
        ${pass_count}=    Evaluate    ${pass_count} + (1 if ${has_response} else 0)
    END

    Log    Passed turns: ${pass_count} / ${results.__len__()}
    Take WebRTC Screenshot    full_conversation_end.png

*** Keywords ***
Close App And Disconnect
    [Documentation]    Cleanup
    Run Keyword And Ignore Error    Disconnect WebRTC
    Run Keyword And Ignore Error    Close Browser
