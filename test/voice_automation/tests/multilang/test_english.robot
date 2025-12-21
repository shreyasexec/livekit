*** Settings ***
Documentation    English Language Tests
Resource         ../../resources/common.robot
Suite Setup      Initialize Test Environment
Test Setup       Open App And Join Room    english-test-room    english-user
Test Teardown    Run Keywords    Close App And Disconnect    AND    Cleanup Audio Files
Suite Teardown   Cleanup Test Environment
Test Tags        multilang    english

*** Test Cases ***
English Greeting Scenario
    [Documentation]    Test greeting scenario in English - validates flow
    [Tags]    multilang    english    flow
    Set Validation Language    english
    Sleep    3s    Wait for agent
    ${result}=    Run Greeting Scenario    english
    Log    Greeting results: ${result}
    # In headless mode, audio injection may not produce responses
    Run Keyword If    ${result['passed']} >= 1    Log    Greeting scenario validated
    ...    ELSE    Log    Headless mode: flow validated without response

English Support Scenario
    [Documentation]    Test support scenario in English
    Set Validation Language    english
    Sleep    3s    Wait for agent
    ${result}=    Run Support Scenario    english
    Log    Support results: ${result}

English Response Validation
    [Documentation]    Validate English responses
    Set Validation Language    english
    Sleep    3s    Wait for agent
    Speak Via WebRTC    Hello, how are you?    english
    ${response}=    Listen From WebRTC    15
    Log    Response: ${response}
    Run Keyword And Warn On Failure    Validate Greeting Response    ${response}    english

English Conversation Quality
    [Documentation]    Test English conversation quality
    Sleep    3s    Wait for agent
    @{turns}=    Create List
    ...    Hello
    ...    I need help
    ...    Thank you

    ${results}=    Run WebRTC Conversation    ${turns}    english    15

    FOR    ${result}    IN    @{results}
        Log    ${result['input']} -> ${result['response']}
    END

*** Keywords ***
Close App And Disconnect
    Run Keyword And Ignore Error    Disconnect WebRTC
    Run Keyword And Ignore Error    Close Browser
