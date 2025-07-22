*** Settings ***
Library           ../../../resources/keywords/final.py
Library           OperatingSystem
Library           JSONLibrary
Library           SSHLibrary
Library           Collections
Library           String
Library           BuiltIn
Resource          ../../../resources/keywords/common_keywords.robot

*** Variables ***
${CONFIG_FILE}    ${CURDIR}/../../../devices/device_config1.json
${LOG_FOLDER}     ${CURDIR}/../../../logs
${DURATION}       10
${BANDWIDTH}      450M

*** Test Cases ***

Full Ethernet Bridging and Performance Test
    [Documentation]    Full test with connectivity, baseline CPU/memory/interrupts, parallel iperf3, post-test stats.
    [Tags]    BB-TRF-BRG-001
    ${config}=    Load JSON From File    ${CONFIG_FILE}
    ${devices}=   Get From Dictionary    ${config}    devices
    ${BB}=    Get From Dictionary    ${devices}    openwrt
    ${PC1}=   Get From Dictionary    ${devices}    PC1
    ${PC2}=   Get From Dictionary    ${devices}    PC2
    ${PC3}=   Get From Dictionary    ${devices}    PC3

    Initialize Custom Log File
    Log Message To Console    ==== Starting Full Ethernet Bridging and Performance Test ====

    Verify PC to PC Connectivity    ${PC1}    ${PC2}    ${PC3}
    Capture Baseline System Stats    ${BB['ip']}    ${BB['username']}    ${BB['password']}

    Ensure Iperf3 Installed On Device    ${PC1}
    Ensure Iperf3 Installed On Device    ${PC2}
    Ensure Iperf3 Installed On Device    ${PC3}

    Configure Port Range    5201    5299
    ${port1}=    Get Next Available Port
    ${port2}=    Get Next Available Port
    ${port3}=    Get Next Available Port
    ${port4}=    Get Next Available Port
    ${port5}=    Get Next Available Port
    ${port6}=    Get Next Available Port

    Log Message To Console    ==== Starting Iperf3 Servers ====
    Start Iperf Server    ${PC1['ip']}    ${PC1['username']}    ${PC1['password']}    ${port1}
    Start Iperf Server    ${PC2['ip']}    ${PC2['username']}    ${PC2['password']}    ${port2}
    Start Iperf Server    ${PC2['ip']}    ${PC2['username']}    ${PC2['password']}    ${port3}
    Start Iperf Server    ${PC3['ip']}    ${PC3['username']}    ${PC3['password']}    ${port4}
    Start Iperf Server    ${PC3['ip']}    ${PC3['username']}    ${PC3['password']}    ${port5}
    Start Iperf Server    ${PC1['ip']}    ${PC1['username']}    ${PC1['password']}    ${port6}

    Sleep    2s

    Log Message To Console    ==== Running Iperf3 Clients in Full Mesh Parallel ====
    Start Monitoring During Iperf    ${BB['ip']}    ${BB['username']}    ${BB['password']}

    Start Iperf Client Parallel    ${PC2['ip']}    ${PC2['username']}    ${PC2['password']}    ${PC1['ip']}    ${DURATION}    ${BANDWIDTH}    ${port1}
    Start Iperf Client Parallel    ${PC1['ip']}    ${PC1['username']}    ${PC1['password']}    ${PC2['ip']}    ${DURATION}    ${BANDWIDTH}    ${port2}
    Start Iperf Client Parallel    ${PC3['ip']}    ${PC3['username']}    ${PC3['password']}    ${PC2['ip']}    ${DURATION}    ${BANDWIDTH}    ${port3}
    Start Iperf Client Parallel    ${PC2['ip']}    ${PC2['username']}    ${PC2['password']}    ${PC3['ip']}    ${DURATION}    ${BANDWIDTH}    ${port4}
    Start Iperf Client Parallel    ${PC1['ip']}    ${PC1['username']}    ${PC1['password']}    ${PC3['ip']}    ${DURATION}    ${BANDWIDTH}    ${port5}
    Start Iperf Client Parallel    ${PC3['ip']}    ${PC3['username']}    ${PC3['password']}    ${PC1['ip']}    ${DURATION}    ${BANDWIDTH}    ${port6}

    Wait For All Iperf Clients
    Stop Monitoring

    Capture Post Test System Stats    ${BB['ip']}    ${BB['username']}    ${BB['password']}
    Log Message To Console    ==== Completed Full Ethernet Bridging and Performance Test ====

*** Keywords ***

Initialize Custom Log File
    Create Directory    ${LOG_FOLDER}
    ${timestamp}=    Get Current Date    %Y%m%d_%H%M%S
    ${custom_log}=    Set Variable    ${LOG_FOLDER}/custom_log_${timestamp}.log
    Set Suite Variable    ${custom_log}
    Log To Console    [${timestamp}] Custom log file initialized: ${custom_log}
    Set Log File Path    ${custom_log}

Get Timestamp
    ${time}=    Get Current Date    %Y-%m-%d %H:%M:%S
    [Return]    ${time}

Capture Baseline System Stats
    [Arguments]    ${BB_IP}    ${USERNAME}    ${PASSWORD}
    SSHLibrary.Open Connection    ${BB_IP}    timeout=15s
    SSHLibrary.Login    ${USERNAME}    ${PASSWORD}
    ${ts}=    Get Timestamp
    Log Message To Console    [${ts}] ==== Capturing Baseline CPU, Memory, Interrupts ====
    ${cpu_output}=    SSHLibrary.Execute Command    sar -u 1 1
    ${mem_output}=    SSHLibrary.Execute Command    sar -r 1 1
    ${intr_output}=   SSHLibrary.Execute Command    cat /proc/interrupts
    Append To File    ${custom_log}    \n[${ts}] ===== Baseline CPU Stats =====\n${cpu_output}\n
    Append To File    ${custom_log}    \n[${ts}] ===== Baseline Memory Stats =====\n${mem_output}\n
    Append To File    ${custom_log}    \n[${ts}] ===== Baseline Interrupt Stats =====\n${intr_output}\n
    SSHLibrary.Close Connection

Capture Post Test System Stats
    [Arguments]    ${BB_IP}    ${USERNAME}    ${PASSWORD}
    SSHLibrary.Open Connection    ${BB_IP}    timeout=15s
    SSHLibrary.Login    ${USERNAME}    ${PASSWORD}
    ${ts}=    Get Timestamp
    Log Message To Console    [${ts}] ==== Capturing Post-Test CPU, Memory, Interrupts ====
    ${cpu_output}=    SSHLibrary.Execute Command    sar -u 1 1
    ${mem_output}=    SSHLibrary.Execute Command    sar -r 1 1
    ${intr_output}=   SSHLibrary.Execute Command    cat /proc/interrupts
    Append To File    ${custom_log}    \n[${ts}] ===== Post-Test CPU Stats =====\n${cpu_output}\n
    Append To File    ${custom_log}    \n[${ts}] ===== Post-Test Memory Stats =====\n${mem_output}\n
    Append To File    ${custom_log}    \n[${ts}] ===== Post-Test Interrupt Stats =====\n${intr_output}\n
    SSHLibrary.Close Connection

Verify PC to PC Connectivity
    [Arguments]    ${PC1}    ${PC2}    ${PC3}
    ${ts}=    Get Timestamp
    Log Message To Console    [${ts}] ==== Verifying Ping Connectivity Among PCs ====
    #Append To File    ${custom_log}    \n[${ts}] ==== Verifying Ping Connectivity Among PCs ====\n
    Check Ping    ${PC1}    ${PC2['ip']}
    Check Ping    ${PC1}    ${PC3['ip']}
    Check Ping    ${PC2}    ${PC1['ip']}
    Check Ping    ${PC2}    ${PC3['ip']}
    Check Ping    ${PC3}    ${PC1['ip']}
    Check Ping    ${PC3}    ${PC2['ip']}

Check Ping
    [Arguments]    ${SOURCE_DEVICE}    ${TARGET_IP}
    ${ts}=    Get Timestamp
    Log Message To Console    [${ts}] --> ${SOURCE_DEVICE['ip']} pinging ${TARGET_IP}
    SSHLibrary.Open Connection    ${SOURCE_DEVICE['ip']}    timeout=1
    SSHLibrary.Login    ${SOURCE_DEVICE['username']}    ${SOURCE_DEVICE['password']}
    ${ping_output}=    SSHLibrary.Execute Command    ping -c 3 ${TARGET_IP}
    Log Message To Console    [${ts}] [${SOURCE_DEVICE['ip']}] Ping Output:\n${ping_output}
    Append To File    ${custom_log}    \n[${ts}] [${SOURCE_DEVICE['ip']}] Ping to ${TARGET_IP}:\n${ping_output}\n
    Should Contain    ${ping_output}    0% packet loss    msg=Ping from ${SOURCE_DEVICE['ip']} to ${TARGET_IP} FAILED!
    SSHLibrary.Close Connection



Ensure Iperf3 Installed On Device
    [Arguments]    ${DEVICE}
    SSHLibrary.Open Connection    ${DEVICE['ip']}    timeout=2s
    SSHLibrary.Login    ${DEVICE['username']}    ${DEVICE['password']}
    Ensure Iperf3 Installed
    SSHLibrary.Close Connection

Ensure Iperf3 Installed
    ${ts}=    Get Timestamp
    ${result}=    SSHLibrary.Execute Command    which iperf3 || echo "NOT_FOUND"
    Run Keyword If    '${result}' == 'NOT_FOUND'    Log Message To Console    [${ts}] iperf3 NOT FOUND on device, proceeding to install
    Run Keyword If    '${result}' == 'NOT_FOUND'    Log Message To Custom File    [${ts}] iperf3 NOT FOUND on device, proceeding to install
    Run Keyword If    '${result}' == 'NOT_FOUND'    Install Iperf3
    Run Keyword If    '${result}' != 'NOT_FOUND'    Log Message To Console    [${ts}] iperf3 already installed on device
    Run Keyword If    '${result}' != 'NOT_FOUND'    Log Message To Custom File    [${ts}] iperf3 already installed on device

Install Iperf3
    ${ts}=    Get Timestamp
    Log Message To Console    [${ts}] Installing iperf3 on device
    Log Message To Custom File    [${ts}] Installing iperf3 on device
    SSHLibrary.Execute Command    apt update -y || true
    SSHLibrary.Execute Command    apt install iperf3 -y
    ${check}=    SSHLibrary.Execute Command    which iperf3 || echo "NOT_FOUND"
    Should Not Contain    ${check}    NOT_FOUND    msg=iperf3 installation failed
    Log Message To Console    [${ts}] iperf3 installation completed successfully
    Log Message To Custom File    [${ts}] iperf3 installation completed successfully






