import paramiko
import time
import os
from robot.api.deco import keyword
from robot.libraries.BuiltIn import BuiltIn

@keyword
def initialize_custom_log_file():
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(os.path.dirname(__file__), "../../../logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"custom_log_{timestamp}.log")
    BuiltIn().set_suite_variable("${LOG_FILE}", log_path)
    with open(log_path, "a") as f:
        f.write(f"[INFO][{time.strftime('%Y-%m-%d %H:%M:%S')}] ==== New Suite Run Started ====\n")
    BuiltIn().log_to_console(f"📂 Custom log initialized: {log_path}")

@keyword
def log_message_to_custom_file(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"[INFO][{timestamp}] {message}\n"
    log_path = BuiltIn().get_variable_value("${LOG_FILE}", default="lan_throughput_results.log")
    BuiltIn().log_to_console(message)
    BuiltIn().log(full_message)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a") as f:
        f.write(full_message)

@keyword
def ping_host(target_ip, source_ip):
    log_message_to_custom_file(f"📡 Pinging {target_ip} from {source_ip}")
    ssh = _connect_ssh(source_ip)
    stdin, stdout, stderr = ssh.exec_command(f"ping -c 4 {target_ip}")
    output = stdout.read().decode()
    log_message_to_custom_file(output)
    ssh.close()

@keyword
def get_resource_stats(device, phase):
    ssh = _connect_ssh(device["ip"], device["user"], device["password"])
    log_message_to_custom_file(f"📊 Collecting [{phase}] stats from {device['ip']}")

    # cpu_cmd = "sar 1 1 | grep 'Average:' || sar 1 1 | grep 'all'"  # CPU avg
    cpu_cmd = "sar -P ALL 1 1"
    mem_cmd = "free -h"  # Memory usage
    intr_cmd = "cat /proc/interrupts | head -20"

    output = ""

    for label, cmd in [("CPU", cpu_cmd), ("MEM", mem_cmd), ("INTR", intr_cmd)]:
        stdin, stdout, _ = ssh.exec_command(cmd)
        out = stdout.read().decode()
        output += f"$ {label} => {cmd}\n{out}\n"

    log_message_to_custom_file(f"📊 [{phase}] Stats:\n{output}")
    ssh.close()


@keyword
def run_full_ethernet_throughput_test(bb, pc, duration, bandwidth):
    port = 5201

    log_message_to_custom_file("📡 PC → BB TCP")
    _run_iperf(bb, server=True)
    _run_inline_monitoring(bb, duration)
    _run_iperf(pc, bb["ip"], duration, tcp=True)

    log_message_to_custom_file("📡 PC → BB UDP")
    _run_iperf(bb, server=True)
    _run_inline_monitoring(bb, duration)
    _run_iperf(pc, bb["ip"], duration, tcp=False, bandwidth=bandwidth)

    log_message_to_custom_file("📡 BB → PC TCP")
    _run_iperf(pc, server=True)
    _run_inline_monitoring(bb, duration)
    _run_iperf(bb, pc["ip"], duration, tcp=True)

    log_message_to_custom_file("📡 BB → PC UDP")
    _run_iperf(pc, server=True)
    _run_inline_monitoring(bb, duration)
    _run_iperf(bb, pc["ip"], duration, tcp=False, bandwidth=bandwidth)

    log_message_to_custom_file("📡 Bidirectional TCP")
    _run_iperf(pc, server=True)
    _run_inline_monitoring(bb, duration)
    _run_iperf(bb, pc["ip"], duration, tcp=True)
    _run_iperf(pc, bb["ip"], duration, tcp=True)

def _run_inline_monitoring(device, duration):
    ssh = _connect_ssh(device["ip"], device["user"], device["password"])
    log_message_to_custom_file(f"🛠️ Running inline monitoring on {device['ip']} for {duration}s during iperf")

    cmd = f"""
    for i in $(seq 1 {duration}); do 
        echo "=== [$(date +%H:%M:%S)] ===";
        sar -P ALL 1 1;
        free -h;
        head -20 /proc/interrupts;
        echo "-----------------------------";
        sleep 1;
    done
    """

    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode()
    ssh.close()

    log_message_to_custom_file(f"📊 [DURING] Monitoring from {device['ip']}:\n{output}")


def _run_iperf(host, target=None, duration=10, tcp=True, bandwidth="1G", server=False):
    ssh = _connect_ssh(host["ip"], host["user"], host["password"])
    if server:
        log_message_to_custom_file(f"🔧 Starting iperf3 server on {host['ip']}")
        ssh.exec_command("pkill iperf3; iperf3 -s -D")
        time.sleep(2)
        ssh.close()
        return

    cmd = f"iperf3 -c {target} -t {duration} -P 5"
    if not tcp:
        cmd += f" -u -b {bandwidth}"

    log_message_to_custom_file(f"🚀 Running iperf3:\n{cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode()
    error = stderr.read().decode()

    if output.strip():
        log_message_to_custom_file(f"📥 iperf3 output:\n{output}")
    if error.strip():
        log_message_to_custom_file(f"⚠️ iperf3 error:\n{error}")

    ssh.close()

def _connect_ssh(ip, user="osboxes", password="spanidea"):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=user, password=password)
    return client

