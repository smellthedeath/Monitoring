# 🚀 Enterprise Observability & Monitoring Stack

A production-ready, highly available, full-stack monitoring and alerting solution powered by **Prometheus**, **Grafana**, **Alertmanager**, and tailored telemetry exporters. 

This repository provides zero-dependency automated deployment, curated alert rules, and pre-built Grafana dashboards for heterogeneous enterprise infrastructure, including **Cisco Core/Access switches**, **MikroTik routers (CRS & RB series)**, **Asterisk / Simotel VoIP PBX**, **Dahua NVR & CCTV Camera fleets**, **Linux/Windows VM clusters**, **HPE ProLiant iLO hardware**, and **VMware vSphere/vCenter**.

---

## 🏛️ Architecture Overview

```
                      +-----------------------------+
                      |       Reverse Proxy         |
                      |   (Nginx TLS Termination)   |
                      +--------------+--------------+
                                     |
               +---------------------+---------------------+
               |                     |                     |
               v                     v                     v
      +-----------------+   +-----------------+   +-----------------+
      |     Grafana     |   |   Prometheus    |   |  Alertmanager   |
      | (Visualizations)|   |  (Core TSDB v3) |   | (Alert Routing) |
      +-----------------+   +--------+--------+   +--------+--------+
                                     |                     |
                   +-----------------+-----------------+   | Webhook
                   | Scrapes                           |   v
                   v                                   v +--------------+
    +------------------------------+                     | Rocket.Chat  |
    |         Exporters            |                     | Notifications|
    |  - Node Exporter (Host/Linux)|                     +--------------+
    |  - Windows Exporter (WMI)    |
    |  - SNMP Exporter (Cisco/MT)  |
    |  - Blackbox (ICMP / HTTPS)   |
    |  - Asterisk AMI Exporter     |
    |  - VMware vCenter Exporter   |
    +------------------------------+
```

---

## 📦 What's Included

### 1. 🌐 Core Network Monitoring
- **Cisco Catalyst Switches (SNMP v2c / IF-MIB)**:
  - 300+ ports bandwidth tracking (`ifHCInOctets` / `ifHCOutOctets`).
  - Core PortChannel (`Po1` - `Po4`) LAG status alerts.
  - Interface operational status (`ifOperStatus`) and packet discards/errors.
- **MikroTik Routers & Switches (Dual-Module: Health + IF-MIB)**:
  - Supports CRS317 Cloud Router Switches and RB1100 series.
  - Optical DDM transceivers (Tx/Rx optical power, module temperatures, loss of signal).
  - Hardware redundancy monitoring: Dual PSUs state, fan RPMs, CPU temperature.
  - Core uplink drops and WAN gateway link tracking.

### 2. 📞 Telephony & VoIP PBX (Asterisk / Simotel)
- **Zero-Dependency Lightweight Python Exporter** (`/exporters/asterisk_exporter/`):
  - Read-only integration with Asterisk Manager Interface (AMI).
  - Collects real-time active calls, active channels, and call volume.
  - SIP peer registrations (status, IP, response latency).
  - Call queue metrics (waiting callers, logged-in agents).
  - Zero Asterisk reload, zero config modification, zero impact on active calls.

### 3. 📹 CCTV & Physical Surveillance
- **Dahua NVR & IP Camera Fleet**:
  - ICMP ping probes with sub-millisecond precision.
  - Real-time online/offline status grid for 25+ IP cameras.
  - Latency jitter graph to detect switch drops or video frame degradation.
  - NVR packet loss and 24-hour availability tracking.

### 4. 💻 Fleet Server Monitoring & Disk Alerts
- **Linux Hosts (Node Exporter)**:
  - CPU, RAM, Load Average, Swap, Systemd service health.
  - **Comprehensive Disk Space Alerts**:
    - `LinuxDiskUsageWarning`: Triggers when any partition (`ext4`, `xfs`, `btrfs`) exceeds **80%**.
    - `LinuxDiskUsageCritical`: Triggers when any partition exceeds **90%**.
    - `LinuxDiskWillFillIn24Hours`: Predictive linear extrapolation estimating exhaustion within 24 hours.
- **Windows Servers (Windows Exporter)**:
  - CPU utilization, memory paging, high disk I/O.
  - **Windows Logical Disk Alerts**:
    - `WindowsDiskUsageWarning`: Triggers when any drive (`C:`, `D:`, `E:`) exceeds **80%**.
    - `WindowsDiskUsageCritical`: Triggers when any drive exceeds **90%**.
    - `WindowsDiskWillFillIn24Hours`: 24-hour predictive fill-up warning.

### 5. 🛡️ Alert Rules & Webhook Notifications
- Curated Prometheus alert rules organized by domain:
  - `cisco_rules.yml`, `mikrotik_rules.yml`, `linux_rules.yml`, `windows_rules.yml`, `voip_rules.yml`, `nvr_cctv_rules.yml`, `blackbox_rules.yml`.
- Standard integration with **Rocket.Chat Webhooks** (supports Slack / Telegram / Microsoft Teams).

---

## 🚀 Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/smellthedeath/Monitoring.git
cd Monitoring
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your passwords and domain:
```bash
cp .env.example .env
nano .env
```

### 3. Start the Stack
```bash
docker compose up -d
```

Verify all containers are healthy:
```bash
docker compose ps
```

---

## 🖥️ Pre-Provisioned Grafana Dashboards

Dashboards are stored in `/grafana/dashboards/` and are automatically imported on startup:

| Dashboard | Description |
|---|---|
| **`mikrotik_network.json`** | Dual-module MikroTik CRS317 & RB1100 hardware health & bandwidth |
| **`cisco_switches.json`** | 5x Cisco Catalyst switches, PortChannels, interface traffic |
| **`asterisk_voip.json`** | Live calls, active channels, SIP peer table, queue summaries |
| **`cctv_nvr.json`** | Dahua NVR availability and 25x IP camera latency grid |
| **`linux_servers.json`** | Linux cluster CPU, RAM, disk usage, and network throughput |
| **`windows_servers.json`** | Windows VMs cluster performance, drive usage, and I/O metrics |
| **`vmware_vsphere.json`** | VMware vCenter hypervisors, datastores, and VM resources |
| **`hpe_ilo.json`** | HP ProLiant server hardware sensors (power supplies, fans, disks) |

---

## 🔒 Security & Best Practices

- **Zero Hardcoded Secrets**: All passwords and credentials are managed via environment variables.
- **Non-Root / Least Privilege**: Container services run with restricted capabilities.
- **Read-Only Telemetry**: Asterisk AMI user and SNMP community strings require read-only access.
- **Automated Backups**: Includes `/scripts/backup-monitoring.sh` with automated 14-day tarball rotation.

---

## 📄 License
MIT License. Built for enterprise infrastructure reliability and resilience.
