*** Settings ***
Library           ../../../resources/keywords/eth-03.py
Library           OperatingSystem
Library           JSONLibrary
Library           SSHLibrary
Library           Collections
Library           String
Library           BuiltIn
Resource          ../../../resources/keywords/common_keywords.robot

Suite Setup       Full Suite Setup
Suite Teardown    Close All Connections

*** Variables ***
${CONFIG_FILE}     ${CURDIR}/../../../devices/eth-03.json
${LOG_FOLDER}      ${CURDIR}/../../../logs

*** Test Cases ***
Ethernet LAN Interface L2 Throughput Test
    [Documentation]    Run unidirectional and bidirectional UDP/TCP iperf3 between PC and BB.
    Log Message To Custom File    ==== Starting LAN Throughput Test ====

    Log Message To Custom File    ✅ Pinging BB to check connectivity
    Ping Host                     ${BB["ip"]}    ${PC["ip"]}

    Log Message To Custom File    📊 Recording CPU/memory stats BEFORE test
    Get Resource Stats            ${BB}    BEFORE

    Log Message To Custom File    🚀 Starting iperf3 traffic tests (TCP/UDP)
    Run Full Ethernet Throughput Test    ${BB}    ${PC}    ${DURATION}    ${BANDWIDTH}

    Log Message To Custom File    📊 Recording CPU/memory stats AFTER test
    Get Resource Stats            ${BB}    AFTER

    Log Message To Custom File    ✅ Test completed

*** Keywords ***
Full Suite Setup
    Initialize Custom Log File
    Load Config And Connect

Load Config And Connect
    Log Message To Custom File    📁 Loading config from ${CONFIG_FILE}
    ${config}=    Load JSON From File    ${CONFIG_FILE}
    Set Suite Variable    ${BB}          ${config["BB"]}
    Set Suite Variable    ${PC}          ${config["PC"]}
    Set Suite Variable    ${DURATION}    ${config["duration"]}
    Set Suite Variable    ${BANDWIDTH}   ${config["bandwidth"]}

    Log Message To Custom File    🔌 Connecting to BB: ${BB["ip"]}
    Open Connection    ${BB["ip"]}
    Login              ${BB["user"]}    ${BB["password"]}

    Log Message To Custom File    🔌 Connecting to PC: ${PC["ip"]}
    Open Connection    ${PC["ip"]}
    Login              ${PC["user"]}    ${PC["password"]}

