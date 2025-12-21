*** Settings ***
Documentation    LiveKit Agent Connection Tests
Resource         ../../resources/common.robot
Suite Setup      Initialize LLM Client
Test Teardown    Disconnect From Room
Suite Teardown   Cleanup API Clients
Test Tags        livekit    connection

*** Variables ***
${AGENT_ROOM}    agent-connect-test

*** Test Cases ***
LLM Should Be Available For Agent
    [Documentation]    Verify LLM is available for agent use
    ${health}=    Check LLM Service Health
    Should Be True    ${health}

TTS Should Be Available For Agent
    [Documentation]    Verify TTS is available for agent use
    Initialize TTS Client
    ${health}=    Check TTS Service Health
    Should Be True    ${health}

Agent Should Generate Greeting
    [Documentation]    Test agent greeting generation
    ${greeting}=    Generate LLM Response    Generate a short greeting for a user who just joined
    Response Should Not Be Empty    ${greeting}
    Log    Agent greeting: ${greeting}

Agent Should Handle User Query
    [Documentation]    Test agent query handling
    ${response}=    Generate LLM Response    The user asks: How can you help me?
    Response Should Not Be Empty    ${response}
    Validate Response Contains Keywords    ${response}    help    assist    support    can
    Log    Query response: ${response}

Agent Response Should Be Synthesizable
    [Documentation]    Test agent response can be synthesized
    Initialize TTS Client
    ${response}=    Generate LLM Response    Say hello to the user
    ${audio}=    Synthesize Speech    ${response}
    Audio File Should Exist    ${audio}
    Audio Should Not Be Silent    ${audio}
    Log    Synthesized response audio: ${audio}
