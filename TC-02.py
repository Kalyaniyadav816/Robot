from robot.api.deco import keyword
from robot.libraries.BuiltIn import BuiltIn
import paramiko
import threading

iperf_threads = []


@keyword("Configure OpenWRT Wireless")
def configure_openwrt_wireless(ip, ssid, psk):
    ssh = _connect(ip, "root")
    cmds = [
        "uci set wireless.@wifi-device[0].disabled='0'",
        "uci set wireless.@wifi-iface[0].network='lan'",
        f"uci set wireless.@wifi-iface[0].ssid='{ssid}'",
        "uci set wireless.@wifi-iface[0].encryption='psk2'",
        f"uci set wireless.@wifi-iface[0].key='{psk}'",
        "uci commit wireless",
        "wifi reload"
    ]
    for cmd in cmds:
        ssh.exec_command(cmd)
        BuiltIn().run_keyword("Log Message To Custom File", f"Executed on OpenWRT: {cmd}")
        BuiltIn().log_to_console(f"Executed on OpenWRT: {cmd}")
    ssh.close()


@keyword
def configure_rpi_static_ip_and_wpa(rpi_ip, username, password, static_ip, ssid, psk, encryption="wpa2"):
    ssh = _connect(rpi_ip, username, password)
    dhcp_config = f"""interface wlan0
static ip_address={static_ip}/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4
"""
    ssh.exec_command("sudo sed -i '/interface wlan0/,/^$/d' /etc/dhcpcd.conf")
    ssh.exec_command(f'echo "{dhcp_config}" | sudo tee -a /etc/dhcpcd.conf > /dev/null')
    BuiltIn().run_keyword("Log Message To Custom File", f"Set static IP on RPi {rpi_ip}: {static_ip}")
    BuiltIn().log_to_console(f"Set static IP on RPi {rpi_ip}: {static_ip}")

    key_mgmt = "WPA-PSK" if encryption.lower() in ["wpa2", "psk2"] else "NONE"
    wpa_content = f"""ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=IN

network={{
    ssid="{ssid}"
    psk="{psk}"
    key_mgmt={key_mgmt}
}}"""
    ssh.exec_command(f'echo "{wpa_content}" | sudo tee /etc/wpa_supplicant/wpa_supplicant.conf > /dev/null')
    BuiltIn().run_keyword("Log Message To Custom File",
                          f"WPA supplicant configured with SSID '{ssid}', encryption '{encryption}'")
    BuiltIn().log_to_console(f"WPA supplicant configured with SSID '{ssid}', encryption '{encryption}'")
    ssh.exec_command("sudo wpa_cli -i wlan0 reconfigure")
    ssh.exec_command("sudo systemctl restart dhcpcd")
    BuiltIn().run_keyword("Log Message To Custom File", f"Reconfigured WiFi and restarted dhcpcd on {rpi_ip}")
    BuiltIn().log_to_console(f"Reconfigured WiFi and restarted dhcpcd on {rpi_ip}")
    ssh.close()


@keyword
def ensure_iperf3_installed(rpi_ip, username, password):
    ssh = _connect(rpi_ip, username, password)
    stdin, stdout, _ = ssh.exec_command("which iperf3")
    if not stdout.read().strip():
        BuiltIn().run_keyword("Log Message To Custom File", f"Installing iperf3 on {rpi_ip}")
        BuiltIn().log_to_console(f"Installing iperf3 on {rpi_ip}")
        ssh.exec_command("sudo apt update && sudo apt install iperf3 -y")
    else:
        BuiltIn().run_keyword("Log Message To Custom File", f"iperf3 already installed on {rpi_ip}")
        BuiltIn().log_to_console(f"iperf3 already installed on {rpi_ip}")
    ssh.close()


@keyword
def start_iperf_server(ip, username, password, port):
    ssh = _connect(ip, username, password)
    ssh.exec_command(f"pkill -f 'iperf3 -s'")
    ssh.exec_command(f"nohup iperf3 -s -p {port} > /tmp/iperf3_server_{port}.log 2>&1 &")
    BuiltIn().run_keyword("Log Message To Custom File", f"Started iperf3 server on {ip}:{port}")
    BuiltIn().log_to_console(f"Started iperf3 server on {ip}:{port}")
    ssh.close()


@keyword
def start_iperf_client_parallel(src_ip, user, password, dest_ip, duration, bandwidth, port):
    def run_client():
        try:
            ssh = _connect(src_ip, user, password)
            cmd = f"iperf3 -c {dest_ip} -t {duration} -b {bandwidth} -p {port}"
            BuiltIn().run_keyword("Log Message To Custom File",
                                  f"Running iperf3 client from {src_ip} to {dest_ip}:{port} in background")
            BuiltIn().log_to_console(f"Running iperf3 client from {src_ip} to {dest_ip}:{port} in background")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            out = stdout.read().decode()
            err = stderr.read().decode()

            if out.strip():
                BuiltIn().run_keyword("Log Message To Custom File", f"[iperf3 OUTPUT from {src_ip} ➜ {dest_ip}]\n{out}")
                BuiltIn().log_to_console(f"[iperf3 OUTPUT from {src_ip} ➜ {dest_ip}]\n{out}")
            if err.strip():
                BuiltIn().run_keyword("Log Message To Custom File", f"[iperf3 ERROR from {src_ip} ➜ {dest_ip}]\n{err}")
                BuiltIn().log_to_console(f"[iperf3 ERROR from {src_ip} ➜ {dest_ip}]\n{err}")

            if exit_status != 0:
                BuiltIn().run_keyword("Log Message To Custom File",
                                      f"[ERROR] iperf3 client exited with code {exit_status}")
                BuiltIn().log_to_console(f"[ERROR] iperf3 client exited with code {exit_status}")
            ssh.close()
        except Exception as e:
            BuiltIn().run_keyword("Log Message To Custom File",
                                  f"[ERROR] Failed to run iperf3 from {src_ip} to {dest_ip}: {e}")
            BuiltIn().log_to_console(f"[ERROR] Failed to run iperf3 from {src_ip} to {dest_ip}: {e}")

    thread = threading.Thread(target=run_client)
    iperf_threads.append(thread)
    thread.start()


@keyword
def wait_for_all_iperf_clients():
    for t in iperf_threads:
        t.join()
    BuiltIn().run_keyword("Log Message To Custom File", "All iperf3 clients finished")
    BuiltIn().log_to_console("All iperf3 clients finished")


@keyword
def fetch_iperf_logs(src_ip, user, password, dest_ip):
    try:
        ssh = _connect(src_ip, user, password)
        log_file = f"/tmp/iperf3_{src_ip.replace('.', '_')}_to_{dest_ip.replace('.', '_')}.log"
        stdin, stdout, stderr = ssh.exec_command(f"cat {log_file}")
        output = stdout.read().decode()
        BuiltIn().run_keyword("Log Message To Custom File", f"[iperf3 OUTPUT from {src_ip} ➜ {dest_ip}]\n{output}")
        BuiltIn().log_to_console(f"[iperf3 OUTPUT from {src_ip} ➜ {dest_ip}]\n{output}")
        ssh.exec_command(f"rm {log_file}")
        ssh.close()
    except Exception as e:
        BuiltIn().run_keyword("Log Message To Custom File",
                              f"[ERROR] Failed to fetch iperf3 log from {src_ip} to {dest_ip}: {e}")
        BuiltIn().log_to_console(f"[ERROR] Failed to fetch iperf3 log from {src_ip} to {dest_ip}: {e}")


@keyword
def capture_baseline_system_stats(ip, user, password):
    BuiltIn().run_keyword("Log Message To Custom File", "Capturing baseline system stats")
    BuiltIn().log_to_console("Capturing baseline system stats")
    ssh = _connect(ip, user, password)
    BuiltIn().run_keyword("Log Message To Custom File", _collect_stats(ssh))
    BuiltIn().log_to_console(_collect_stats(ssh))
    ssh.close()


@keyword
def capture_post_test_system_stats(ip, user, password):
    BuiltIn().run_keyword("Log Message To Custom File", "Capturing post-test system stats")
    BuiltIn().log_to_console("Capturing post-test system stats")
    ssh = _connect(ip, user, password)
    BuiltIn().run_keyword("Log Message To Custom File", _collect_stats(ssh))
    BuiltIn().log_to_console(_collect_stats(ssh))
    ssh.close()


@keyword
def start_monitoring_during_iperf(ip, user, password):
    BuiltIn().run_keyword("Log Message To Custom File", "Starting monitoring during iperf")
    BuiltIn().log_to_console("Starting monitoring during iperf")


@keyword
def stop_monitoring():
    BuiltIn().run_keyword("Log Message To Custom File", " Monitoring stopped")
    BuiltIn().log_to_console(" Monitoring stopped")

def _monitor_resource_usage_timed(ip, user, password, duration):
    ssh = _connect(ip, user, password)
    start_time = time.time()

    while time.time() - start_time < duration:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # CPU & Memory
            stdin, stdout, _ = ssh.exec_command("top -bn1 | head -n 5")
            top_output = stdout.read().decode()

            # Memory
            stdin, stdout, _ = ssh.exec_command("free -m")
            mem_output = stdout.read().decode()

            # Interrupts
            stdin, stdout, _ = ssh.exec_command("cat /proc/interrupts | head -n 15")
            irq_output = stdout.read().decode()

            message = (
                f"\n[MONITORING - {timestamp}] === CPU & Memory ===\n{top_output}"
                f"\n[MONITORING - {timestamp}] === Free Memory ===\n{mem_output}"
                f"\n[MONITORING - {timestamp}] === Interrupts ===\n{irq_output}"
            )
            BuiltIn().run_keyword("Log Message To Custom File", message)
            BuiltIn().log_to_console(message)

        except Exception as e:
            BuiltIn().run_keyword("Log Message To Custom File", f"[ERROR] Monitoring error: {e}")
            BuiltIn().log_to_console(f"[ERROR] Monitoring error: {e}")
        time.sleep(1)

    ssh.close()
    BuiltIn().run_keyword("Log Message To Custom File", "✅ Monitoring finished after duration")
    BuiltIn().log_to_console("✅ Monitoring finished after duration")


def _collect_stats(ssh):
    cmds = ["free -m", "cat /proc/interrupts", "top -bn1 | head -20"]
    result = ""
    for cmd in cmds:
        stdin, stdout, _ = ssh.exec_command(cmd)
        result += f"\n$ {cmd}\n{stdout.read().decode()}"
    return result


def _connect(ip, username, password="root"):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=username, password=password)
    return ssh

