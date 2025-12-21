*** Settings ***
Documentation    WebRTC UI Flow Tests
Resource         ../../resources/common.robot
Test Setup       Open Browser With Permissions    headless=${TRUE}
Test Teardown    Run Keywords    Close App And Disconnect    AND    Cleanup Audio Files
Test Tags        webrtc    ui

*** Variables ***
${ROOM}          ui-flow-test
${USER}          ui-flow-user

*** Test Cases ***
UI Should Show Connection Status
    [Documentation]    Verify UI shows connection status
    Navigate To App
    Enter Room Details    ${ROOM}    ${USER}
    Click Join Room Button
    Wait For Room Connection    30
    # Voice agent UI should be visible
    Page Should Contain Text    Voice Agent
    Take WebRTC Screenshot    ui_connected.png

UI Should Show Speaking Indicators
    [Documentation]    Verify UI shows speaking indicators
    Navigate To App
    Enter Room Details    ${ROOM}    ${USER}
    Click Join Room Button
    Wait For Room Connection    30
    # Check for speaking indicator elements
    ${page_content}=    Get Transcript Text
    Log    Page transcript content: ${page_content}

UI Should Show Transcript Panel
    [Documentation]    Verify transcript panel is visible
    Navigate To App
    Open App And Join Room    ${ROOM}    ${USER}
    # Transcript should be visible
    Page Should Contain Text    Transcript
    Take WebRTC Screenshot    ui_transcript.png

Complete UI Flow Should Work
    [Documentation]    Test complete UI interaction flow
    [Tags]    e2e
    Navigate To App

    # Step 1: Enter room details
    Enter Room Details    ${ROOM}    ${USER}

    # Step 2: Join room
    Click Join Room Button
    Wait For Room Connection    30

    # Step 3: Verify connected state
    WebRTC Should Be Connected

    # Step 4: Take screenshot
    Take WebRTC Screenshot    ui_complete_flow.png

    # Step 5: Disconnect
    Click Disconnect Button

    Log    Complete UI flow test passed

*** Keywords ***
Close App And Disconnect
    [Documentation]    Cleanup
    Run Keyword And Ignore Error    Disconnect WebRTC
    Run Keyword And Ignore Error    Close Browser
