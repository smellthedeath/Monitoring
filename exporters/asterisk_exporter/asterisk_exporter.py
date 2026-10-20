#!/usr/bin/env python3
"""
Lightweight Asterisk Prometheus Exporter for Asterisk / Simotel / FreePBX.
Collects real-time channels, active calls, SIP peers, and queue metrics via AMI.
Zero external dependencies (Python 3 standard library only).
"""
import os
import socket
import time
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configuration (Supports Environment Variables or Defaults)
AMI_HOST = os.getenv("ASTERISK_AMI_HOST", "127.0.0.1")
AMI_PORT = int(os.getenv("ASTERISK_AMI_PORT", "5038"))
AMI_USER = os.getenv("ASTERISK_AMI_USER", "ami_user")
AMI_PASS = os.getenv("ASTERISK_AMI_PASS", "ChangeMeAmiPassword")
EXPORTER_PORT = int(os.getenv("ASTERISK_EXPORTER_PORT", "9200"))
CACHE_TTL = float(os.getenv("EXPORTER_CACHE_TTL", "5.0"))  # Seconds

# Thread-safe Cache
cache_lock = threading.Lock()
last_scrape_time = 0
cached_metrics = ""

def fetch_ami_metrics():
    global last_scrape_time, cached_metrics
    now = time.time()
    with cache_lock:
        if now - last_scrape_time < CACHE_TTL and cached_metrics:
            return cached_metrics

    metrics = []
    up = 0
    active_calls = 0
    active_channels = 0
    sip_peers = []
    queues = []

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect((AMI_HOST, AMI_PORT))
        s.recv(512)
        
        # AMI Login
        s.sendall(f"Action: Login\r\nUsername: {AMI_USER}\r\nSecret: {AMI_PASS}\r\n\r\n".encode())
        time.sleep(0.05)
        login_resp = s.recv(1024).decode("utf-8", errors="ignore")
        if "Success" in login_resp:
            up = 1

            # CoreStatus
            s.sendall(b"Action: CoreStatus\r\n\r\n")
            time.sleep(0.05)
            core_resp = s.recv(2048).decode("utf-8", errors="ignore")
            m = re.search(r"CoreCurrentCalls:\s*(\d+)", core_resp)
            if m:
                active_calls = int(m.group(1))

            # CoreShowChannels
            s.sendall(b"Action: CoreShowChannels\r\n\r\n")
            time.sleep(0.1)
            raw_chan = ""
            while True:
                chunk = s.recv(4096).decode("utf-8", errors="ignore")
                raw_chan += chunk
                if "EventList: Complete" in chunk or "CoreShowChannelsComplete" in chunk or not chunk:
                    break
            
            chan_events = raw_chan.count("Event: CoreShowChannel\r\n")
            m_chans = re.search(r"ListItems:\s*(\d+)", raw_chan)
            if m_chans:
                active_channels = int(m_chans.group(1))
            elif chan_events > 0:
                active_channels = chan_events

            # SIPpeers
            s.sendall(b"Action: SIPpeers\r\n\r\n")
            time.sleep(0.15)
            raw_sip = ""
            while True:
                chunk = s.recv(8192).decode("utf-8", errors="ignore")
                raw_sip += chunk
                if "EventList: Complete" in chunk or "PeerlistComplete" in chunk or not chunk:
                    break
            
            entries = raw_sip.split("Event: PeerEntry\r\n")
            for entry in entries[1:]:
                peer_name = ""
                ip = ""
                status_raw = ""
                latency = 0.0
                is_ok = 0
                
                m_p = re.search(r"ObjectName:\s*([^\r\n]+)", entry)
                if m_p:
                    peer_name = m_p.group(1).strip()
                m_ip = re.search(r"IPaddress:\s*([^\r\n]+)", entry)
                if m_ip:
                    ip = m_ip.group(1).strip()
                m_st = re.search(r"Status:\s*([^\r\n]+)", entry)
                if m_st:
                    status_raw = m_st.group(1).strip()
                
                if "OK" in status_raw:
                    is_ok = 1
                    m_lat = re.search(r"\((\d+)\s*ms\)", status_raw)
                    if m_lat:
                        latency = float(m_lat.group(1)) / 1000.0

                if peer_name:
                    sip_peers.append({
                        "peer": peer_name,
                        "ip": ip,
                        "status": is_ok,
                        "latency": latency,
                        "status_text": status_raw
                    })

            # QueueSummary
            s.sendall(b"Action: QueueSummary\r\n\r\n")
            time.sleep(0.1)
            raw_q = ""
            while True:
                chunk = s.recv(4096).decode("utf-8", errors="ignore")
                raw_q += chunk
                if "EventList: Complete" in chunk or "QueueSummaryComplete" in chunk or not chunk:
                    break
            
            q_entries = raw_q.split("Event: QueueSummary\r\n")
            for q_e in q_entries[1:]:
                q_name = ""
                callers = 0
                members = 0
                m_qn = re.search(r"Queue:\s*([^\r\n]+)", q_e)
                if m_qn:
                    q_name = m_qn.group(1).strip()
                m_c = re.search(r"Callers:\s*(\d+)", q_e)
                if m_c:
                    callers = int(m_c.group(1))
                m_m = re.search(r"LoggedIn:\s*(\d+)", q_e)
                if m_m:
                    members = int(m_m.group(1))
                if q_name:
                    queues.append({
                        "queue": q_name,
                        "callers": callers,
                        "members": members
                    })

            s.sendall(b"Action: Logoff\r\n\r\n")
        s.close()
    except Exception:
        up = 0

    # Format Prometheus Exposition
    metrics.append("# HELP asterisk_up Asterisk AMI connection status (1 = UP, 0 = DOWN)")
    metrics.append("# TYPE asterisk_up gauge")
    metrics.append(f"asterisk_up {up}")

    if up == 1:
        metrics.append("# HELP asterisk_active_calls Number of currently active calls")
        metrics.append("# TYPE asterisk_active_calls gauge")
        metrics.append(f"asterisk_active_calls {active_calls}")

        metrics.append("# HELP asterisk_active_channels Number of active channels")
        metrics.append("# TYPE asterisk_active_channels gauge")
        metrics.append(f"asterisk_active_channels {active_channels}")

        online_count = sum(1 for p in sip_peers if p["status"] == 1)
        offline_count = len(sip_peers) - online_count

        metrics.append("# HELP asterisk_sip_peers_total Total configured SIP peers")
        metrics.append("# TYPE asterisk_sip_peers_total gauge")
        metrics.append(f"asterisk_sip_peers_total {len(sip_peers)}")

        metrics.append("# HELP asterisk_sip_peers_online Number of online/reachable SIP peers")
        metrics.append("# TYPE asterisk_sip_peers_online gauge")
        metrics.append(f"asterisk_sip_peers_online {online_count}")

        metrics.append("# HELP asterisk_sip_peers_offline Number of offline/unreachable SIP peers")
        metrics.append("# TYPE asterisk_sip_peers_offline gauge")
        metrics.append(f"asterisk_sip_peers_offline {offline_count}")

        metrics.append("# HELP asterisk_sip_peer_status SIP peer registration status (1 = OK, 0 = Offline/Unknown)")
        metrics.append("# TYPE asterisk_sip_peer_status gauge")
        for p in sip_peers:
            metrics.append(f'asterisk_sip_peer_status{{peer="{p["peer"]}",ip="{p["ip"]}"}} {p["status"]}')

        metrics.append("# HELP asterisk_sip_peer_latency_seconds Latency of SIP peer in seconds")
        metrics.append("# TYPE asterisk_sip_peer_latency_seconds gauge")
        for p in sip_peers:
            if p["latency"] > 0:
                metrics.append(f'asterisk_sip_peer_latency_seconds{{peer="{p["peer"]}"}} {p["latency"]}')

        if queues:
            metrics.append("# HELP asterisk_queue_callers Number of callers currently waiting in queue")
            metrics.append("# TYPE asterisk_queue_callers gauge")
            for q in queues:
                metrics.append(f'asterisk_queue_callers{{queue="{q["queue"]}"}} {q["callers"]}')

            metrics.append("# HELP asterisk_queue_members Number of logged-in agents in queue")
            metrics.append("# TYPE asterisk_queue_members gauge")
            for q in queues:
                metrics.append(f'asterisk_queue_members{{queue="{q["queue"]}"}} {q["members"]}')

    result = "\n".join(metrics) + "\n"
    with cache_lock:
        last_scrape_time = time.time()
        cached_metrics = result
    return result

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics" or self.path == "/":
            payload = fetch_ami_metrics().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def run():
    server_address = ("0.0.0.0", EXPORTER_PORT)
    httpd = HTTPServer(server_address, MetricsHandler)
    print(f"Asterisk Prometheus Exporter listening on port {EXPORTER_PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()

if __name__ == "__main__":
    run()
