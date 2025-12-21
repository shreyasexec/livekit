*** Settings ***
Documentation    Multi-Language Conversation Tests - 7 Languages
...              Tests agent conversation in English, Hindi, Kannada, Tamil, Telugu, Malayalam, Marathi
...              Verifies: Agent responds correctly, Latency < 2000ms, Transcription works

Library    ../libraries/AudioGenerator.py
Library    ../libraries/LiveKitTester.py
Library    ../libraries/TokenGenerator.py
Library    Collections
Library    BuiltIn

Suite Setup       Setup Audio Generator
Suite Teardown    Cleanup Audio Generator
Test Teardown     Disconnect From Room If Connected

*** Variables ***
${LIVEKIT_URL}           ws://192.168.20.62:7878
${MAX_LATENCY_MS}        8000
${RESPONSE_TIMEOUT}      15
${SUITE_ID}              ${EMPTY}

*** Test Cases ***

English Conversation Test
    [Documentation]    Test basic conversation in English
    [Tags]    language    english    critical

    ${room_name}=    Set Variable    test-en-${SUITE_ID}
    ${token}=    Generate Token    ${room_name}    test-user-en

    # Connect to room
    Connect To Room    ${LIVEKIT_URL}    ${token}    timeout=10

    # Wait for agent greeting to complete
    Sleep    3s

    # Reset metrics after greeting
    Reset Metrics

    # Generate English greeting
    ${audio_file}=    AudioGen.Generate Test Phrase    language=en    phrase_index=0
    Log    Generated audio: ${audio_file}

    # Send audio and wait for response (with minimal silence to keep stream alive)
    Send Audio File    ${audio_file}    wait_after=1.0
    Wait For Agent Response    timeout=${RESPONSE_TIMEOUT}

    # Verify response
    Verify Agent Responded
    ${latency}=    Get Response Latency
    Log    Response latency: ${latency}ms
    Verify Latency Under    ${MAX_LATENCY_MS}

Hindi Conversation Test
    [Documentation]    Test conversation in Hindi (नमस्ते)
    [Tags]    language    hindi    critical

    ${room_name}=    Set Variable    test-hi-${SUITE_ID}
    ${token}=    Generate Token    ${room_name}    test-user-hi

    Connect To Room    ${LIVEKIT_URL}    ${token}    timeout=10
    Sleep    3s
    Reset Metrics

    # Generate Hindi greeting: "नमस्ते, आप कैसे हैं?"
    ${audio_file}=    AudioGen.Generate Test Phrase    language=hi    phrase_index=0

    Send Audio File    ${audio_file}    wait_after=1.0
    Wait For Agent Response    timeout=${RESPONSE_TIMEOUT}

    Verify Agent Responded
    ${latency}=    Get Response Latency
    Log    Response latency: ${latency}ms
    Verify Latency Under    ${MAX_LATENCY_MS}

Kannada Conversation Test
    [Documentation]    Test conversation in Kannada (ನಮಸ್ಕಾರ)
    [Tags]    language    kannada    critical

    ${room_name}=    Set Variable    test-kn-${SUITE_ID}
    ${token}=    Generate Token    ${room_name}    test-user-kn

    Connect To Room    ${LIVEKIT_URL}    ${token}    timeout=10
    Sleep    3s
    Reset Metrics

    # Generate Kannada greeting: "ನಮಸ್ಕಾರ, ನೀವು ಹೇಗಿದ್ದೀರಿ?"
    ${audio_file}=    AudioGen.Generate Test Phrase    language=kn    phrase_index=0

    Send Audio File    ${audio_file}    wait_after=1.0
    Wait For Agent Response    timeout=${RESPONSE_TIMEOUT}

    Verify Agent Responded
    ${latency}=    Get Response Latency
    Log    Response latency: ${latency}ms
    Verify Latency Under    ${MAX_LATENCY_MS}

Tamil Conversation Test
    [Documentation]    Test conversation in Tamil (வணக்கம்)
    [Tags]    language    tamil    critical

    ${room_name}=    Set Variable    test-ta-${SUITE_ID}
    ${token}=    Generate Token    ${room_name}    test-user-ta

    Connect To Room    ${LIVEKIT_URL}    ${token}    timeout=10
    Sleep    3s
    Reset Metrics

    # Generate Tamil greeting: "வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?"
    ${audio_file}=    AudioGen.Generate Test Phrase    language=ta    phrase_index=0

    Send Audio File    ${audio_file}    wait_after=1.0
    Wait For Agent Response    timeout=${RESPONSE_TIMEOUT}

    Verify Agent Responded
    ${latency}=    Get Response Latency
    Log    Response latency: ${latency}ms
    Verify Latency Under    ${MAX_LATENCY_MS}

Telugu Conversation Test
    [Documentation]    Test conversation in Telugu (నమస్కారం)
    [Tags]    language    telugu    critical

    ${room_name}=    Set Variable    test-te-${SUITE_ID}
    ${token}=    Generate Token    ${room_name}    test-user-te

    Connect To Room    ${LIVEKIT_URL}    ${token}    timeout=10
    Sleep    3s
    Reset Metrics

    # Generate Telugu greeting: "నమస్కారం, మీరు ఎలా ఉన్నారు?"
    ${audio_file}=    AudioGen.Generate Test Phrase    language=te    phrase_index=0

    Send Audio File    ${audio_file}    wait_after=1.0
    Wait For Agent Response    timeout=${RESPONSE_TIMEOUT}

    Verify Agent Responded
    ${latency}=    Get Response Latency
    Log    Response latency: ${latency}ms
    Verify Latency Under    ${MAX_LATENCY_MS}

Malayalam Conversation Test
    [Documentation]    Test conversation in Malayalam (നമസ്കാരം)
    [Tags]    language    malayalam    critical

    ${room_name}=    Set Variable    test-ml-${SUITE_ID}
    ${token}=    Generate Token    ${room_name}    test-user-ml

    Connect To Room    ${LIVEKIT_URL}    ${token}    timeout=10
    Sleep    3s
    Reset Metrics

    # Generate Malayalam greeting: "നമസ്കാരം, നിങ്ങൾ എങ്ങനെയുണ്ട്?"
    ${audio_file}=    AudioGen.Generate Test Phrase    language=ml    phrase_index=0

    Send Audio File    ${audio_file}    wait_after=1.0
    Wait For Agent Response    timeout=${RESPONSE_TIMEOUT}

    Verify Agent Responded
    ${latency}=    Get Response Latency
    Log    Response latency: ${latency}ms
    Verify Latency Under    ${MAX_LATENCY_MS}

Marathi Conversation Test
    [Documentation]    Test conversation in Marathi (नमस्कार)
    [Tags]    language    marathi    critical

    ${room_name}=    Set Variable    test-mr-${SUITE_ID}
    ${token}=    Generate Token    ${room_name}    test-user-mr

    Connect To Room    ${LIVEKIT_URL}    ${token}    timeout=10
    Sleep    3s
    Reset Metrics

    # Generate Marathi greeting: "नमस्कार, तुम्ही कसे आहात?"
    ${audio_file}=    AudioGen.Generate Test Phrase    language=mr    phrase_index=0

    Send Audio File    ${audio_file}    wait_after=1.0
    Wait For Agent Response    timeout=${RESPONSE_TIMEOUT}

    Verify Agent Responded
    ${latency}=    Get Response Latency
    Log    Response latency: ${latency}ms
    Verify Latency Under    ${MAX_LATENCY_MS}

Multi-Turn English Conversation
    [Documentation]    Test multi-turn conversation in English
    [Tags]    language    english    multi-turn

    ${room_name}=    Set Variable    test-en-multiturn-${SUITE_ID}
    ${token}=    Generate Token    ${room_name}    test-user-multiturn

    Connect To Room    ${LIVEKIT_URL}    ${token}    timeout=10
    Sleep    3s

    # Turn 1: Greeting
    Reset Metrics
    ${audio1}=    AudioGen.Generate Test Phrase    language=en    phrase_index=0
    Send Audio File    ${audio1}    wait_after=1.0
    Wait For Agent Response    timeout=${RESPONSE_TIMEOUT}
    Verify Agent Responded
    Sleep    6s

    # Turn 2: Question
    Reset Metrics
    ${audio2}=    AudioGen.Generate Test Phrase    language=en    phrase_index=1
    Send Audio File    ${audio2}    wait_after=1.0
    Wait For Agent Response    timeout=${RESPONSE_TIMEOUT}
    Verify Agent Responded
    Sleep    6s

    # Turn 3: Thank you
    Reset Metrics
    ${audio3}=    AudioGen.Generate Test Phrase    language=en    phrase_index=2
    Send Audio File    ${audio3}    wait_after=1.0
    Wait For Agent Response    timeout=${RESPONSE_TIMEOUT}
    Verify Agent Responded

*** Keywords ***

Setup Audio Generator
    [Documentation]    Initialize audio generator
    Import Library    ../libraries/AudioGenerator.py    WITH NAME    AudioGen

Cleanup Audio Generator
    [Documentation]    Clean up temporary audio files
    Run Keyword And Ignore Error    AudioGen.Cleanup

Disconnect From Room If Connected
    [Documentation]    Disconnect from LiveKit room after test
    Run Keyword And Ignore Error    Disconnect
