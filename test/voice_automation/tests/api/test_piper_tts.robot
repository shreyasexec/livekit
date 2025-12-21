*** Settings ***
Documentation    Tests for Piper TTS API
Resource         ../../resources/common.robot
Suite Setup      Initialize TTS Client
Suite Teardown   Run Keywords    Cleanup API Clients    AND    Cleanup Audio Files
Test Tags        api    tts

*** Test Cases ***
Piper TTS Service Should Be Healthy
    [Documentation]    Verify Piper TTS service is running
    ${result}=    Check TTS Service Health
    Should Be True    ${result}

TTS Should Synthesize Simple Text
    [Documentation]    Verify TTS synthesizes simple text
    ${audio_path}=    Synthesize Speech    Hello, this is a test.
    Audio File Should Exist    ${audio_path}
    Audio Duration Should Be Greater Than    ${audio_path}    0.5
    Log    Audio file: ${audio_path}

TTS Should Synthesize English Text
    [Documentation]    Verify TTS synthesizes English text
    ${audio_path}=    Verify TTS Synthesis    How are you doing today?    en
    Log    English audio: ${audio_path}

TTS Should Produce Non-Silent Audio
    [Documentation]    Verify TTS audio is not silent
    ${audio_path}=    Synthesize Speech    Testing one two three
    Audio Should Not Be Silent    ${audio_path}
    Log    Audio file: ${audio_path}

TTS Should Handle Long Text
    [Documentation]    Verify TTS handles longer text
    ${long_text}=    Set Variable    This is a longer piece of text that should be synthesized correctly. It contains multiple sentences and should produce audio that is several seconds long.
    ${audio_path}=    Synthesize Speech    ${long_text}
    Audio File Should Exist    ${audio_path}
    Audio Duration Should Be Greater Than    ${audio_path}    3.0
    Log    Long audio: ${audio_path}

TTS Should Handle Special Characters
    [Documentation]    Verify TTS handles punctuation and special characters
    ${audio_path}=    Synthesize Speech    Hello! How are you? I'm doing well, thank you.
    Audio File Should Exist    ${audio_path}
    Audio Should Not Be Silent    ${audio_path}

TTS Synthesis Time Should Be Acceptable
    [Documentation]    Verify TTS synthesis is fast enough
    ${audio_path}=    Synthesize Speech    Quick synthesis test
    ${time}=    Get TTS Synthesis Time
    Log    Synthesis time: ${time}ms
    Should Be True    ${time} < 5000    TTS synthesis took too long: ${time}ms

TTS Should Generate Correct Sample Rate
    [Documentation]    Verify TTS audio has correct sample rate
    ${audio_path}=    Synthesize Speech    Sample rate test
    ${sample_rate}=    Get Audio Sample Rate    ${audio_path}
    Log    Sample rate: ${sample_rate}
    Should Be True    ${sample_rate} >= 16000
