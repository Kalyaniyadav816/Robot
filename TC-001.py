import threading
import subprocess
import time
from datetime import datetime
from robot.api.deco import keyword
import paramiko

# Global Variables
client_threads = []
port_range_start = 5201
port_range_end = 5299
allocated_ports = []
log_file_path = None
monitoring_flag = False
monitoring_lock = threading.Lock()
port_lock = threading.Lock()

# ================= General Logging =================

def log_message_to_console(message):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    log_line = f"{timestamp} {message}"
    print(log_line)
    if log_file_path:
        with open(log_file_path, "a") as f:
            f.write(log_line + "\n")

@keyword
def set_log_file_path(path):
    global log_file_path
    log_file_path = path
    with open(log_file_path, "a") as f:
        f.write(f"\n=== Log Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    log_message_to_console(f"Custom log file set to: {path}")

# ================= Port Management =================

@keyword
def configure_port_range(start, end):
    global port_range_start, port_range_end, allocated_ports
    port_range_start = int(start)
    port_range_end = int(end)
    allocated_ports = []
    log_message_to_console(f"Port range configured: {start} to {end}")

@keyword
def get_next_available_port():
    with port_lock:
        for port in range(port_range_start, port_range_end + 1):
            if port not in allocated_ports:
                allocated_ports.append(port)
                log_message_to_console(f"Assigned next available port: {port}")
                return port
    raise Exception("No available ports in the configured range")

# ================= Iperf3 Management =================

@keyword
def start_iperf_server(server_ip, server_user, server_pass, port):
    log_message_to_console(f"Starting iperf3 server on {server_ip} port {port}")
    cmd = (
        f"sshpass -p {server_pass} ssh -o StrictHostKeyChecking=no {server_user}@{server_ip} "
        f"'nohup iperf3 -s -p {port} > /dev/null 2>&1 &'"
    )
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    log_message_to_console(f"iperf3 server command output:\n{result.stdout}")

@keyword
def start_iperf_client_parallel(client_ip, client_user, client_pass, server_ip, duration, bandwidth, port):
    thread = threading.Thread(target=_run_iperf_client, args=(client_ip, client_user, client_pass, server_ip, duration, bandwidth, port))
    thread.start()
    client_threads.append(thread)

@keyword
def wait_for_all_iperf_clients():
    for thread in client_threads:
        thread.join()
    client_threads.clear()
    log_message_to_console("All iperf3 client threads completed")

def _run_iperf_client(client_ip, client_user, client_pass, server_ip, duration, bandwidth, port):
    log_message_to_console(f"Starting iperf3 client {client_ip} -> {server_ip}:{port} for {duration}s")
    cmd = (
        f"sshpass -p {client_pass} ssh -o StrictHostKeyChecking=no {client_user}@{client_ip} "
        f"'iperf3 -c {server_ip} -p {port} -t {duration} -b {bandwidth} -P 1'"
    )
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    log_message_to_console(f"Iperf3 output {client_ip} -> {server_ip}:{port}:\n{result.stdout}")

# ================= Monitoring Functions =================

@keyword
def start_monitoring_during_iperf(bb_ip, bb_user, bb_pass, interval=1):
    global monitoring_flag
    with monitoring_lock:
        monitoring_flag = True
    thread = threading.Thread(target=_collect_resource_usage, args=(bb_ip, bb_user, bb_pass, interval))
    thread.start()
    log_message_to_console(f"Started real-time resource monitoring on OpenWRT every {interval}s")

@keyword
def stop_monitoring():
    global monitoring_flag
    with monitoring_lock:
        monitoring_flag = False
    log_message_to_console("Stopped real-time resource monitoring on OpenWRT")

def _collect_resource_usage(bb_ip, bb_user, bb_pass, interval):
    retries = 3
    for attempt in range(retries):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(bb_ip, username=bb_user, password=bb_pass)

            log_message_to_console("Connected to OpenWRT for resource monitoring")
            with open(log_file_path, 'a') as f:
                f.write("\n===== Real-time Monitoring Started =====\n")

            while True:
                start_time = time.time()

                with monitoring_lock:
                    if not monitoring_flag:
                        break

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # CPU usage
                stdin, stdout, stderr = ssh.exec_command("sar 1 1 | grep 'Average' || true")
                cpu = stdout.read().decode()

                # Memory usage
                stdin, stdout, stderr = ssh.exec_command("free -m")
                mem = stdout.read().decode()

                # Interrupts
                stdin, stdout, stderr = ssh.exec_command("cat /proc/interrupts | head -20")
                interrupts = stdout.read().decode()

                with open(log_file_path, 'a') as f:
                    f.write(f"\n===== Timestamp: {timestamp} =====\n")
                    f.write("\n[CPU Usage]\n" + cpu)
                    f.write("\n[Memory Usage]\n" + mem)
                    f.write("\n[Interrupts (First 20 Lines)]\n" + interrupts + "\n")

                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                time.sleep(sleep_time)

            ssh.close()
            with open(log_file_path, 'a') as f:
                f.write("\n===== Real-time Monitoring Stopped =====\n")
            log_message_to_console("Real-time monitoring stopped and SSH session closed")
            return

        except Exception as e:
            log_message_to_console(f"Monitoring SSH connection error (attempt {attempt + 1}): {str(e)}")
            time.sleep(2)

    log_message_to_console("Failed to establish monitoring SSH connection after multiple attempts")

