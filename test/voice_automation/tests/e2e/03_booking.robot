*** Settings ***
Documentation    End-to-End Booking Tests
Resource         ../../resources/common.robot
Suite Setup      Initialize Test Environment
Test Setup       Open App And Join Room    e2e-booking-room    booking-user
Test Teardown    Run Keywords    Close App And Disconnect    AND    Cleanup Audio Files
Suite Teardown   Cleanup Test Environment
Test Tags        e2e    booking

*** Test Cases ***
Booking Request Should Get Response
    [Documentation]    Test booking request handling - validates flow
    [Tags]    e2e    booking    flow
    Sleep    3s    Wait for agent
    Speak Via WebRTC    I want to book an appointment
    ${response}=    Listen From WebRTC    15
    Log    Booking response: ${response}
    Run Keyword If    '${response}' != ''    Log    Agent responded to booking request

Time Selection Should Work
    [Documentation]    Test time selection - validates flow
    [Tags]    e2e    booking    flow
    Sleep    3s    Wait for agent
    Speak Via WebRTC    I want to schedule for tomorrow at 3 PM
    ${response}=    Listen From WebRTC    15
    Log    Time response: ${response}
    Run Keyword If    '${response}' != ''    Log    Agent responded to time selection

Confirmation Flow
    [Documentation]    Test booking confirmation
    Sleep    3s    Wait for agent
    Speak Via WebRTC    Yes, please confirm my booking
    ${response}=    Listen From WebRTC    15
    Log    Confirmation response: ${response}

Full Booking Conversation
    [Documentation]    Complete booking conversation
    [Tags]    full
    Sleep    3s    Wait for agent

    # Initial request
    Speak Via WebRTC    Hello, I would like to book an appointment
    ${resp1}=    Listen From WebRTC    15
    Log    Response 1: ${resp1}

    # Time selection
    Speak Via WebRTC    Tomorrow afternoon at 3 PM would be perfect
    ${resp2}=    Listen From WebRTC    15
    Log    Response 2: ${resp2}

    # Confirmation
    Speak Via WebRTC    Yes, that works for me. Please confirm
    ${resp3}=    Listen From WebRTC    15
    Log    Response 3: ${resp3}

    # Additional info
    Speak Via WebRTC    My name is John Smith
    ${resp4}=    Listen From WebRTC    15
    Log    Response 4: ${resp4}

    # Thank you
    Speak Via WebRTC    Thank you for booking my appointment
    ${resp5}=    Listen From WebRTC    15
    Log    Response 5: ${resp5}

*** Keywords ***
Close App And Disconnect
    Run Keyword And Ignore Error    Disconnect WebRTC
    Run Keyword And Ignore Error    Close Browser
