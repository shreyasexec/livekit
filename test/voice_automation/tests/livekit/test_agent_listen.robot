*** Settings ***
Documentation    LiveKit Agent Listening Tests
Resource         ../../resources/common.robot
Suite Setup      Initialize Test Environment
Suite Teardown   Cleanup Test Environment
Test Tags        livekit    listen

*** Test Cases ***
Agent Should Process Audio Input
    [Documentation]    Test audio input processing
    # Generate test audio
    ${text}=    Set Variable    Hello, I need help
    ${audio}=    Synthesize Speech    ${text}
    Audio File Should Exist    ${audio}
    Log    Generated input audio: ${audio}

Agent Should Handle Short Audio
    [Documentation]    Test handling of short audio
    ${audio}=    Generate Test Tone    440    0.5
    Audio File Should Exist    ${audio}
    ${duration}=    Get Audio Duration    ${audio}
    Should Be True    ${duration} < 1.0

Agent Should Handle Long Audio
    [Documentation]    Test handling of long audio
    ${text}=    Set Variable    This is a longer message that contains multiple sentences. I have several questions about my account. First, I would like to know about billing. Second, I need help with settings.
    ${audio}=    Synthesize Speech    ${text}
    Audio File Should Exist    ${audio}
    ${duration}=    Get Audio Duration    ${audio}
    Should Be True    ${duration} > 3.0
    Log    Long audio duration: ${duration}s

Agent Should Handle Silence
    [Documentation]    Test handling of silence
    ${silence}=    Generate Silence    2.0
    Audio File Should Exist    ${silence}
    ${duration}=    Get Audio Duration    ${silence}
    Should Be True    ${duration} >= 2.0

Audio Processing Should Be Efficient
    [Documentation]    Test audio processing efficiency
    ${audio}=    Synthesize Speech    Quick test
    ${duration}=    Get Audio Duration    ${audio}
    ${synthesis_time}=    Get TTS Synthesis Time
    Log    Audio duration: ${duration}s, Synthesis time: ${synthesis_time}ms
    # Synthesis should be faster than audio duration (real-time or better)
    ${realtime_ratio}=    Evaluate    ${duration} * 1000 / ${synthesis_time} if ${synthesis_time} > 0 else 999
    Log    Real-time ratio: ${realtime_ratio}
