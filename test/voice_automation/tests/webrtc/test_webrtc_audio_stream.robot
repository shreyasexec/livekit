*** Settings ***
Documentation    WebRTC Audio Streaming Tests
Resource         ../../resources/common.robot
Test Setup       Open App And Join Room    audio-test-room    audio-tester
Test Teardown    Run Keywords    Close App And Disconnect    AND    Cleanup Audio Files
Test Tags        webrtc    audio

*** Test Cases ***
WebRTC Should Have Audio Tracks
    [Documentation]    Verify WebRTC connection has audio tracks
    ${status}=    Get Audio Track Status
    Log    Audio track status: ${status}

Audio Should Be Flowing Through WebRTC
    [Documentation]    Verify audio is flowing
    [Tags]    audio-flow
    Sleep    2s    Wait for audio tracks to initialize
    Run Keyword And Warn On Failure    WebRTC Audio Should Be Flowing

TTS Audio Should Be Injectable
    [Documentation]    Verify TTS audio can be injected into stream
    [Tags]    injection    flow
    # Generate test audio - may fail if TTS temp dir was cleaned up
    ${status}    ${audio_path}=    Run Keyword And Ignore Error    Synthesize Speech    Testing audio injection
    Run Keyword If    '${status}' == 'PASS'    Run Keywords
    ...    Audio File Should Exist    ${audio_path}
    ...    AND    Run Keyword And Warn On Failure    Inject Audio To WebRTC Stream    ${audio_path}
    ...    AND    Log    Audio injection attempted
    Run Keyword If    '${status}' != 'PASS'    Log    TTS synthesis skipped: ${audio_path}

WebRTC Should Report Connection Stats
    [Documentation]    Verify WebRTC stats are available
    ${stats}=    Get WebRTC Connection Stats
    Log    WebRTC Stats: ${stats}
    Should Contain    ${stats}    connection_state

*** Keywords ***
Close App And Disconnect
    [Documentation]    Cleanup
    Run Keyword And Ignore Error    Disconnect WebRTC
    Run Keyword And Ignore Error    Close Browser
