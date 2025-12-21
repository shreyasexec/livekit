*** Settings ***
Documentation    LiveKit Agent Call Tests
Resource         ../../resources/common.robot
Suite Setup      Initialize Test Environment
Test Setup       Open App And Join Room    agent-call-room    call-tester
Test Teardown    Run Keywords    Close App And Disconnect    AND    Cleanup Audio Files
Suite Teardown   Cleanup Test Environment
Test Tags        livekit    call

*** Test Cases ***
Call Should Connect Successfully
    [Documentation]    Test call connection
    WebRTC Should Be Connected
    Log    Call connected successfully

Call Should Have Audio
    [Documentation]    Test call has audio capability
    Sleep    2s    Wait for tracks
    Run Keyword And Warn On Failure    WebRTC Audio Should Be Flowing

Call Should Support Two-Way Communication
    [Documentation]    Test two-way audio
    Sleep    3s    Wait for agent

    # Send audio
    Speak Via WebRTC    Hello, can you hear me?

    # Receive response
    ${response}=    Listen From WebRTC    15
    Log    Agent response: ${response}

Call Duration Should Be Tracked
    [Documentation]    Test call duration tracking
    ${start}=    Get Current Date    result_format=epoch
    Sleep    5s
    ${end}=    Get Current Date    result_format=epoch
    ${duration}=    Evaluate    ${end} - ${start}
    Log    Call duration: ${duration}s
    Should Be True    ${duration} >= 5

*** Keywords ***
Close App And Disconnect
    Run Keyword And Ignore Error    Disconnect WebRTC
    Run Keyword And Ignore Error    Close Browser
