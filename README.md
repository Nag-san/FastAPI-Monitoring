# FastAPI Monitoring & Observability Stack

A complete observability solution for FastAPI applications featuring metrics, logs, and traces using Prometheus, Grafana, Loki, and OpenTelemetry.

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker)
![Grafana](https://img.shields.io/badge/Grafana-F46800?style=for-the-badge&logo=grafana)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus)
![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-000000?style=for-the-badge&logo=opentelemetry)
![Loki](https://img.shields.io/badge/Loki-2C3E50?style=for-the-badge&logo=grafana)


## Features

- **Real-time Metrics** - Request count, latency, and error tracking with Prometheus
- **Structured Logging** - JSON-formatted logs with Loki integration
- **Distributed Tracing** - End-to-end request tracing with OpenTelemetry
- **Error Simulation** - Realistic error scenarios for comprehensive testing
- **Dockerized Setup** - One-command deployment with Docker Compose
- **Pre-built Dashboards** - Beautiful Grafana dashboards out of the box
- **Traffic Generation** - Built-in traffic simulator for load testing



## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for traffic simulation)

### Installation & Running

1. **Clone and setup the project**
   ```bash
   git clone https://github.com/yourusername/fastapi-monitoring-demo.git
   cd fastapi-monitoring-demo
   docker compose up -d
   python traffic-simulator.py

2. **Access the services**
- FastAPI Application: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Grafana Dashboard: http://localhost:3000 (admin/admin)
- Prometheus UI: http://localhost:9090

3. **Project Structure**
   ```bash
   monitoring-demo/
    ├── app/                    # FastAPI application
    │   ├── main.py            # Main application with instrumentation
    │   ├── requirements.txt   # Python dependencies
    │   └── Dockerfile         # Container configuration
    ├── prometheus/
    │   └── prometheus.yml     # Prometheus configuration
    ├── grafana/
    │   └── provisioning/      # Grafana datasources & dashboards
    ├── docker-compose.yml     # Multi-container setup
    ├── otel-collector-config.yaml # OpenTelemetry configuration
    ├── traffic-simulator.py   # Traffic generation script
    └── README.md


## Monitoring Capabilities
1. **Metrics Collected**
- request_count_total - Total HTTP requests with labels (method, endpoint, status)
- request_latency_seconds - Request latency distribution histogram
- error_count_total - Error counts categorized by type and endpoint

2. **Logging Features**
- Structured JSON logging for easy parsing
- Trace context propagation for correlation
- Multi-level logging (INFO, WARNING, ERROR)
- Loki integration for log aggregation and querying


