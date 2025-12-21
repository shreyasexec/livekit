*** Settings ***
Documentation    Tests for Ollama LLM API
Resource         ../../resources/common.robot
Suite Setup      Initialize LLM Client
Suite Teardown   Cleanup API Clients
Test Setup       Clear LLM Conversation History
Test Tags        api    llm

*** Test Cases ***
Ollama Service Should Be Healthy
    [Documentation]    Verify Ollama service is running and model is available
    ${result}=    Check LLM Service Health
    Should Be True    ${result}

LLM Should Generate Response For Simple Prompt
    [Documentation]    Verify LLM generates response for simple prompts
    ${response}=    Generate LLM Response    Hello, how are you?
    Response Should Not Be Empty    ${response}
    Log    Response: ${response}

LLM Should Generate Contextual Response
    [Documentation]    Verify LLM generates contextual responses
    ${response}=    Generate LLM Response    What is the capital of France?
    Validate Response Contains Keywords    ${response}    Paris    capital    France
    Log    Response: ${response}

LLM Should Handle Greeting
    [Documentation]    Verify LLM handles greetings appropriately
    ${response}=    Verify LLM Response Quality    Hello!    hello    hi    hey    greetings
    Log    Greeting Response: ${response}

LLM Should Handle Help Requests
    [Documentation]    Verify LLM handles help requests
    ${response}=    Verify LLM Response Quality    I need help    help    assist    support
    Log    Help Response: ${response}

LLM Should Maintain Conversation Context
    [Documentation]    Verify LLM maintains context across turns
    Clear LLM Conversation History
    ${resp1}=    Generate LLM Response    My name is John
    Log    First response: ${resp1}
    ${resp2}=    Generate LLM Response    What is my name?
    Validate Response Contains Keywords    ${resp2}    John    name
    Log    Second response: ${resp2}

LLM Response Time Should Be Acceptable
    [Documentation]    Verify LLM response time is within limits
    ${response}=    Generate LLM Response    Hello
    ${time}=    Get LLM Response Time
    Log    Response time: ${time}ms
    Should Be True    ${time} < 10000    LLM response took too long: ${time}ms

LLM Should Handle Multi-Sentence Input
    [Documentation]    Verify LLM handles complex input
    ${response}=    Generate LLM Response    I have a problem with my account. It shows an error when I try to log in. Can you help me?
    Response Should Not Be Empty    ${response}
    Validate Response Contains Keywords    ${response}    account    help    error    login    try    issue
    Log    Response: ${response}
