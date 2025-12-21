*** Settings ***
Documentation    Common resources for Voice AI Test Automation
Library          Collections
Library          String
Library          OperatingSystem
Library          DateTime
Library          ../resources/keywords/api_keywords.py
Library          ../resources/keywords/browser_keywords.py
Library          ../resources/keywords/audio_keywords.py
Library          ../resources/keywords/livekit_keywords.py
Library          ../resources/keywords/webrtc_keywords.py
Library          ../resources/keywords/validation_keywords.py

*** Variables ***
${APP_URL}                  https://192.168.20.62:3000/
${OLLAMA_URL}               http://192.168.1.120:11434
${PIPER_URL}                http://192.168.20.62:5500/
${WHISPER_WS_URL}           ws://192.168.1.120:8765/
${DEFAULT_ROOM}             test-room
${DEFAULT_USER}             test-user
${DEFAULT_TIMEOUT}          15
${WEBRTC_TIMEOUT}           20

*** Keywords ***
Initialize Test Environment
    [Documentation]    Initialize all clients and verify services
    Initialize All Clients
    ${llm_health}=    Check LLM Service Health
    ${tts_health}=    Check TTS Service Health
    Log    LLM Health: ${llm_health}
    Log    TTS Health: ${tts_health}

Cleanup Test Environment
    [Documentation]    Cleanup all resources
    Cleanup API Clients
    Cleanup Audio Files

Open App And Join Room
    [Documentation]    Open browser and join voice room
    [Arguments]    ${room_name}=${DEFAULT_ROOM}    ${user_name}=${DEFAULT_USER}    ${headless}=${TRUE}
    Open App With WebRTC Permissions    headless=${headless}
    Join Room Via WebRTC    ${room_name}    ${user_name}
    Wait For WebRTC Connection    ${WEBRTC_TIMEOUT}

Close App And Disconnect
    [Documentation]    Disconnect and close browser
    Disconnect WebRTC

Run Greeting Scenario
    [Documentation]    Run a basic greeting scenario
    [Arguments]    ${language}=english
    Set Validation Language    ${language}
    ${inputs}=    Get Scenario User Inputs    greeting    ${language}
    ${responses}=    Create List
    FOR    ${input}    IN    @{inputs}
        Speak Via WebRTC    ${input}    ${language}
        ${response}=    Listen From WebRTC    ${DEFAULT_TIMEOUT}
        Append To List    ${responses}    ${response}
    END
    ${result}=    Run Scenario Validation    ${responses}    greeting    ${language}
    RETURN    ${result}

Run Support Scenario
    [Documentation]    Run a support scenario
    [Arguments]    ${language}=english
    Set Validation Language    ${language}
    ${inputs}=    Get Scenario User Inputs    support    ${language}
    ${responses}=    Create List
    FOR    ${input}    IN    @{inputs}
        Speak Via WebRTC    ${input}    ${language}
        ${response}=    Listen From WebRTC    ${DEFAULT_TIMEOUT}
        Append To List    ${responses}    ${response}
    END
    ${result}=    Run Scenario Validation    ${responses}    support    ${language}
    RETURN    ${result}

Verify LLM Response Quality
    [Documentation]    Verify LLM response is meaningful
    [Arguments]    ${prompt}    @{expected_keywords}
    ${response}=    Generate LLM Response    ${prompt}
    Response Should Not Be Empty    ${response}
    Validate Response Contains Keywords    ${response}    ${expected_keywords}
    RETURN    ${response}

Verify TTS Synthesis
    [Documentation]    Verify TTS synthesis produces valid audio
    [Arguments]    ${text}    ${language}=en
    ${audio_path}=    Synthesize Speech In Language    ${text}    ${language}
    Audio File Should Exist    ${audio_path}
    Audio Duration Should Be Greater Than    ${audio_path}    0.1
    Audio Should Not Be Silent    ${audio_path}
    RETURN    ${audio_path}

Run Full Conversation Test
    [Documentation]    Run a full conversation test with multiple turns
    [Arguments]    ${turns}    ${language}=english    ${timeout}=${DEFAULT_TIMEOUT}
    Set Validation Language    ${language}
    ${results}=    Run WebRTC Conversation    ${turns}    ${language}    ${timeout}
    RETURN    ${results}

Log Performance Metrics
    [Documentation]    Log performance metrics
    ${llm_time}=    Get LLM Response Time
    ${tts_time}=    Get TTS Synthesis Time
    Log    LLM Response Time: ${llm_time}ms
    Log    TTS Synthesis Time: ${tts_time}ms

Take Failure Screenshot
    [Documentation]    Take screenshot on test failure
    [Teardown]
    ${status}=    Evaluate    'FAIL' in '''${TEST_STATUS}'''
    Run Keyword If    ${status}    Take WebRTC Screenshot    failure_${TEST_NAME}.png
