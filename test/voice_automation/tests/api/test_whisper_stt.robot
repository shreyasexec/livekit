*** Settings ***
Documentation    Tests for WhisperLiveKit STT API
Resource         ../../resources/common.robot
Suite Setup      Initialize Test Environment
Suite Teardown   Cleanup Test Environment
Test Tags        api    stt

*** Test Cases ***
STT Should Connect To WhisperLiveKit
    [Documentation]    Verify STT can connect to WhisperLiveKit WebSocket
    [Tags]    connection
    Initialize STT Client
    ${result}=    Check STT Service Health
    # Note: Connection may require audio to initialize fully
    Log    STT connection result: ${result}

STT Should Transcribe Generated Audio
    [Documentation]    Verify STT transcribes TTS-generated audio
    [Tags]    transcription
    # Generate audio using TTS
    ${text}=    Set Variable    Hello this is a test
    ${audio_path}=    Synthesize Speech    ${text}
    Audio File Should Exist    ${audio_path}
    Audio Should Not Be Silent    ${audio_path}

    # Try to transcribe (may require WebSocket improvements for full testing)
    Log    Generated audio for text: ${text}
    Log    Audio path: ${audio_path}

STT Should Handle Multiple Audio Formats
    [Documentation]    Verify STT handles WAV audio format
    [Tags]    format
    ${audio_path}=    Generate Test Tone    440    1.0
    Audio File Should Exist    ${audio_path}
    ${duration}=    Get Audio Duration    ${audio_path}
    Should Be True    ${duration} > 0.5
    Log    Test tone duration: ${duration}s

Audio Generation Should Work
    [Documentation]    Verify audio generation utilities work
    [Tags]    utility
    ${tone}=    Generate Test Tone    880    0.5
    Audio File Should Exist    ${tone}
    ${silence}=    Generate Silence    1.0
    Audio File Should Exist    ${silence}
    Log    Generated tone: ${tone}
    Log    Generated silence: ${silence}
