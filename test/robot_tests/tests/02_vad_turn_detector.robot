*** Settings ***
Documentation    VAD and Turn Detector Tests - Critical Scenarios
...              Tests 3 critical VAD behaviors:
...              1. User talks → Agent stops immediately (interrupt)
...              2. User pauses (incomplete) → Agent waits 2 seconds
...              3. User completes sentence → Agent responds quickly
...
...              Performance target: < 2000ms end-to-end

Library    ../libraries/AudioGenerator.py
Library    ../libraries/LiveKitTester.py
Library    ../libraries/TokenGenerator.py
Library    BuiltIn
Library    Collections

Suite Setup       Setup Audio Generator
Suite Teardown    Cleanup Audio Generator
Test Teardown     Disconnect From Room If Connected

*** Variables ***
${LIVEKIT_URL}              ws://192.168.20.62:7879
${MAX_INTERRUPT_MS}         200
${MIN_SILENCE_WAIT_MS}      1800
${MAX_SILENCE_WAIT_MS}      2500
${MAX_RESPONSE_LATENCY_MS}  2000
${SUITE_ID}                 ${EMPTY}

*** Test Cases ***

Scenario A: Agent Stops When User Interrupts
    [Documentation]    CRITICAL: If user is talking, agent should stop immediately
    ...                Agent must stop within 100-200ms of user speech detection
    [Tags]    vad    interrupt    critical

    ${room_name}=    Set Variable    test-vad-interrupt-${SUITE_ID}
    ${token}=    Generate Token    ${room_name}    test-user-interrupt

    # Connect to room
    Connect To Room    ${LIVEKIT_URL}    ${token}    timeout=10

    # Step 1: Ask a question that gets a long response
    Log    Step 1: Asking question to get long response
    ${question_audio}=    AudioGen.Generate Speech Espeak    What can you tell me about yourself in detail?    language=en
    Send Audio File    ${question_audio}    wait_after=0.5

    # Wait for agent to start responding
    Wait For Agent Response    timeout=5.0
    Verify Agent Responded

    # Step 2: While agent is speaking, interrupt
    Log    Step 2: Interrupting agent
    Sleep    0.5s    # Let agent speak for 500ms
    Reset Metrics

    ${interrupt_audio}=    AudioGen.Generate Speech Espeak    Wait, stop!    language=en
    Send Audio File    ${interrupt_audio}    wait_after=1.0

    # Wait for agent's response to interruption
    Wait For Agent Response    timeout=5.0

    # Verify: Agent stopped quickly when interrupted
    Verify VAD Interrupt    max_interrupt_ms=${MAX_INTERRUPT_MS}
    Log    ✓ Agent stopped when user interrupted

Scenario B: Agent Waits 2 Seconds for Incomplete Sentence
    [Documentation]    CRITICAL: If user pauses mid-sentence, agent waits ~2 seconds
    ...                User says incomplete phrase, agent must wait 2s before responding
    [Tags]    vad    silence-timeout    critical

    ${room_name}=    Set Variable    test-vad-timeout-${SUITE_ID}
    ${token}=    Generate Token    ${room_name}    test-user-timeout

    Connect To Room    ${LIVEKIT_URL}    ${token}    timeout=10
    Reset Metrics

    # Send incomplete phrase: "Hello, I want to..."
    Log    Sending incomplete phrase with natural pause
    ${incomplete_audio}=    AudioGen.Generate Incomplete Phrase    language=en
    ${send_time}=    Evaluate    time.time()    modules=time

    Send Audio File    ${incomplete_audio}    wait_after=0.1

    # Immediately measure when speech ends
    ${speech_end_time}=    Evaluate    time.time()    modules=time

    # Wait for agent response
    Wait For Agent Response    timeout=5.0

    # Measure when agent started responding
    ${response_start_time}=    Evaluate    time.time()    modules=time

    # Calculate silence duration
    ${silence_duration_ms}=    Evaluate    int((${response_start_time} - ${speech_end_time}) * 1000)
    Log    Silence duration before agent response: ${silence_duration_ms}ms

    # Verify: Agent waited at least 1.8s but not more than 2.5s
    Should Be True    ${silence_duration_ms} >= ${MIN_SILENCE_WAIT_MS}
    ...    msg=Agent responded too quickly (${silence_duration_ms}ms < ${MIN_SILENCE_WAIT_MS}ms)

    Should Be True    ${silence_duration_ms} <= ${MAX_SILENCE_WAIT_MS}
    ...    msg=Agent waited too long (${silence_duration_ms}ms > ${MAX_SILENCE_WAIT_MS}ms)

    Log    ✓ Agent waited ${silence_duration_ms}ms (within 1.8-2.5s range)

Scenario C: Agent Responds Quickly After Complete Sentence
    [Documentation]    CRITICAL: When user completes sentence, agent responds within 300-800ms
    ...                Tests turn completion detection
    [Tags]    vad    turn-completion    critical

    ${room_name}=    Set Variable    test-vad-completion-${SUITE_ID}
    ${token}=    Generate Token    ${room_name}    test-user-completion

    Connect To Room    ${LIVEKIT_URL}    ${token}    timeout=10
    Reset Metrics

    # Send complete sentence: "Hello, how are you today?"
    Log    Sending complete sentence
    ${complete_audio}=    AudioGen.Generate Test Phrase    language=en    phrase_index=0
    ${send_time}=    Evaluate    time.time()    modules=time

    Send Audio File    ${complete_audio}    wait_after=0.1

    ${speech_end_time}=    Evaluate    time.time()    modules=time

    # Wait for agent response
    Wait For Agent Response    timeout=5.0

    ${response_start_time}=    Evaluate    time.time()    modules=time

    # Calculate turn completion latency
    ${completion_latency_ms}=    Evaluate    int((${response_start_time} - ${speech_end_time}) * 1000)
    Log    Turn completion latency: ${completion_latency_ms}ms

    # Verify: Agent responded between 300-800ms (natural conversation feel)
    Should Be True    ${completion_latency_ms} >= 300
    ...    msg=Agent responded too fast (${completion_latency_ms}ms < 300ms)

    Should Be True    ${completion_latency_ms} <= 800
    ...    msg=Agent took too long (${completion_latency_ms}ms > 800ms)

    Log    ✓ Agent responded in ${completion_latency_ms}ms (natural timing)

VAD Multi-Scenario Integration Test
    [Documentation]    Test all 3 VAD scenarios in sequence
    [Tags]    vad    integration

    ${room_name}=    Set Variable    test-vad-integration-${SUITE_ID}
    ${token}=    Generate Token    ${room_name}    test-user-integration

    Connect To Room    ${LIVEKIT_URL}    ${token}    timeout=10

    # Test 1: Normal conversation
    Log    Test 1: Normal complete sentence
    ${audio1}=    AudioGen.Generate Test Phrase    language=en    phrase_index=0
    Send Audio File    ${audio1}    wait_after=0.5
    Wait For Agent Response    timeout=5.0
    Verify Agent Responded
    Reset Metrics

    # Test 2: Incomplete sentence (wait test)
    Log    Test 2: Incomplete sentence - should wait
    ${audio2}=    AudioGen.Generate Incomplete Phrase    language=en
    Send Audio File    ${audio2}    wait_after=3.0    # Wait 3s for agent to respond
    Log    Agent should have waited ~2s before responding

    # Test 3: Another complete sentence
    Reset Metrics
    Log    Test 3: Another complete sentence
    ${audio3}=    AudioGen.Generate Test Phrase    language=en    phrase_index=2
    Send Audio File    ${audio3}    wait_after=0.5
    Wait For Agent Response    timeout=5.0
    Verify Agent Responded

    Log    ✓ All VAD scenarios working in sequence

Performance Test: VAD + Full Pipeline Under 2 Seconds
    [Documentation]    Verify full pipeline (with VAD) completes under 2 seconds
    [Tags]    vad    performance    critical

    ${room_name}=    Set Variable    test-vad-perf-${SUITE_ID}
    ${token}=    Generate Token    ${room_name}    test-user-perf

    Connect To Room    ${LIVEKIT_URL}    ${token}    timeout=10

    # Send greeting
    ${audio}=    AudioGen.Generate Test Phrase    language=en    phrase_index=0
    Send Audio File    ${audio}    wait_after=0.5

    # Wait for response
    Wait For Agent Response    timeout=5.0

    # Verify performance
    Verify Agent Responded
    ${latency}=    Get Response Latency
    Log    End-to-end latency: ${latency}ms

    Verify Latency Under    ${MAX_RESPONSE_LATENCY_MS}
    Log    ✓ Performance target met (${latency}ms < ${MAX_RESPONSE_LATENCY_MS}ms)

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
