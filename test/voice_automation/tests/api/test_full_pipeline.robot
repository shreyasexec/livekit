*** Settings ***
Documentation    Full Voice Pipeline Integration Tests
Resource         ../../resources/common.robot
Suite Setup      Initialize Test Environment
Suite Teardown   Cleanup Test Environment
Test Tags        api    pipeline    integration

*** Variables ***
${TEST_PROMPT}    Hello, how can I help you today?

*** Test Cases ***
Full Pipeline Should Work End To End
    [Documentation]    Test complete voice pipeline: TTS -> (simulated STT) -> LLM -> TTS
    [Tags]    e2e

    # Step 1: Generate user speech (TTS)
    ${user_text}=    Set Variable    Hello, I need some help
    ${user_audio}=    Synthesize Speech    ${user_text}
    Audio File Should Exist    ${user_audio}
    Log    User audio generated: ${user_audio}

    # Step 2: Simulate transcription result
    ${transcription}=    Set Variable    ${user_text}

    # Step 3: Generate LLM response
    ${llm_response}=    Generate LLM Response    ${transcription}
    Response Should Not Be Empty    ${llm_response}
    Log    LLM Response: ${llm_response}

    # Step 4: Synthesize response (TTS)
    ${response_audio}=    Synthesize Speech    ${llm_response}
    Audio File Should Exist    ${response_audio}
    Audio Should Not Be Silent    ${response_audio}
    Log    Response audio generated: ${response_audio}

Pipeline Should Handle Greeting Scenario
    [Documentation]    Test greeting scenario through pipeline
    [Tags]    scenario
    Clear LLM Conversation History

    @{greetings}=    Create List    Hello    How are you    Goodbye

    FOR    ${greeting}    IN    @{greetings}
        ${audio}=    Synthesize Speech    ${greeting}
        ${response}=    Generate LLM Response    ${greeting}
        Response Should Not Be Empty    ${response}
        ${response_audio}=    Synthesize Speech    ${response}
        Audio Should Not Be Silent    ${response_audio}
        Log    ${greeting} -> ${response}
    END

Pipeline Should Maintain Context
    [Documentation]    Test conversation context is maintained
    [Tags]    context
    Clear LLM Conversation History

    # First message
    ${response1}=    Generate LLM Response    My name is Alice and I work at TechCorp
    Log    Response 1: ${response1}

    # Second message referencing first
    ${response2}=    Generate LLM Response    Where do I work?
    Validate Response Contains Keywords    ${response2}    TechCorp    work    company
    Log    Response 2: ${response2}

    # Third message
    ${response3}=    Generate LLM Response    What is my name?
    Validate Response Contains Keywords    ${response3}    Alice    name
    Log    Response 3: ${response3}

Pipeline Performance Should Be Acceptable
    [Documentation]    Test pipeline latency
    [Tags]    performance

    # Measure TTS
    ${start}=    Get Current Date    result_format=epoch
    ${audio}=    Synthesize Speech    Performance test
    ${tts_time}=    Get TTS Synthesis Time

    # Measure LLM
    ${response}=    Generate LLM Response    Hello
    ${llm_time}=    Get LLM Response Time

    # Measure response TTS
    ${response_audio}=    Synthesize Speech    ${response}
    ${tts2_time}=    Get TTS Synthesis Time

    ${total}=    Evaluate    ${tts_time} + ${llm_time} + ${tts2_time}
    Log    TTS1: ${tts_time}ms, LLM: ${llm_time}ms, TTS2: ${tts2_time}ms, Total: ${total}ms

    Should Be True    ${total} < 15000    Pipeline too slow: ${total}ms

Pipeline Should Handle Error Recovery
    [Documentation]    Test pipeline handles errors gracefully
    [Tags]    error

    # Valid request should work
    ${response}=    Generate LLM Response    Valid test request
    Response Should Not Be Empty    ${response}

    # Audio with valid content
    ${audio}=    Synthesize Speech    Error recovery test
    Audio Should Not Be Silent    ${audio}
