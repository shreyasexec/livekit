*** Settings ***
Documentation    WebRTC Connection Tests
Resource         ../../resources/common.robot
Test Setup       Log    Starting WebRTC connection test
Test Teardown    Run Keyword If Test Failed    Take Failure Screenshot
Suite Teardown   Close App And Disconnect
Test Tags        webrtc    connection

*** Variables ***
${ROOM_NAME}     webrtc-test-room
${USER_NAME}     webrtc-test-user

*** Test Cases ***
Browser Should Open With WebRTC Permissions
    [Documentation]    Verify browser opens with microphone permissions
    [Tags]    smoke
    Open Browser With Permissions    headless=${TRUE}
    Navigate To App

App Should Load Successfully
    [Documentation]    Verify voice AI app loads
    [Tags]    smoke
    Open App With WebRTC Permissions    headless=${TRUE}
    Page Should Contain Text    LiveKit

Room Join Form Should Be Visible
    [Documentation]    Verify room join form is displayed
    Open App With WebRTC Permissions    headless=${TRUE}
    Wait For Element    input[placeholder*="room"]
    Wait For Element    input[placeholder*="name"]
    Element Should Be Visible    button:has-text("Join")

User Should Be Able To Enter Room Details
    [Documentation]    Verify room details can be entered
    Open App With WebRTC Permissions    headless=${TRUE}
    Enter Room Details    ${ROOM_NAME}    ${USER_NAME}
    Log    Room details entered successfully

Join Button Should Connect To Room
    [Documentation]    Verify clicking join connects to room
    [Tags]    connection
    Open App With WebRTC Permissions    headless=${TRUE}
    Enter Room Details    ${ROOM_NAME}    ${USER_NAME}
    Click Join Room Button
    Wait For Room Connection    30
    Log    Room connection established

WebRTC Connection Should Be Established
    [Documentation]    Verify WebRTC connection is active
    [Tags]    connection
    Open App And Join Room    ${ROOM_NAME}    ${USER_NAME}
    WebRTC Should Be Connected
    Log    WebRTC connection verified

Disconnect Button Should Disconnect From Room
    [Documentation]    Verify disconnect button works
    Open App And Join Room    ${ROOM_NAME}    ${USER_NAME}
    Click Disconnect Button
    Log    Disconnected from room

*** Keywords ***
Close App And Disconnect
    [Documentation]    Cleanup browser
    Run Keyword And Ignore Error    Disconnect WebRTC
    Run Keyword And Ignore Error    Close Browser
