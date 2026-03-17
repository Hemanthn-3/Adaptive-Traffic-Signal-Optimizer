# 🚦 Smart Traffic Management System

AI-powered adaptive traffic signal control with YOLOv8 vehicle detection, dynamic signal optimization, and emergency green-corridor support — all in one Docker Compose stack.

---

## 🏗️ Architecture

```
Browser Dashboard (React + Vite)
         │  WebSocket / REST
         ▼
  FastAPI Backend  ─── Redis (state cache)
         │               │
         │          MQTT (Mosquitto)
         │               │
  YOLOv8 pipeline ──────►│── Signal hardware / simulator
         │
  PostgreSQL + TimescaleDB (time-series storage)
```

---

## 📋 Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ |
| Docker | 24+ |
| Docker Compose | v2+ |

---

## 🚀 Quick Start

### 1. Clone and configure

```bash
git clone <repo-url>
cd smart-traffic-system
cp .env.example .env
# Edit .env if you need to change passwords / ports
```

### 2. Start infrastructure (PostgreSQL, Redis, Mosquitto)

```bash
docker-compose up postgres redis mosquitto -d
```

Wait ~10 seconds for PostgreSQL to be healthy:
```bash
docker-compose ps   # all three should show "healthy" or "running"
```

### 3. Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
cd ..
```

### 4. Run database migrations

```bash
cd backend
alembic upgrade head
cd ..
```

This creates all tables and converts `density_readings` and `signal_events` into TimescaleDB hypertables.

### 5. Start the backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at → **http://localhost:8000/docs**

### 6. Install and start the frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard available at → **http://localhost:5173**

### 7. Run the demo

Place a `.mp4` traffic video in `ml/test_videos/`, then:

```bash
# From the project root:
python demo.py ml/test_videos/sample.mp4
```

Or just run without arguments to be prompted:
```bash
python demo.py
```

**What the demo does:**
- Checks Redis and PostgreSQL connectivity
- Processes your video frame-by-frame with YOLOv8
- Prints a live table every 30 frames showing density + signal timing
- Automatically triggers a simulated ambulance emergency at frame 100
- Prints full summary stats at the end

---

## 🔥 Full Docker Stack (all services)

```bash
docker-compose up --build
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:5173 |
| API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| MQTT broker | localhost:1883 |
| MQTT WebSocket | localhost:9001 |

---

## ⚡ API Reference

### Traffic
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/traffic/intersections` | List all intersections |
| `GET` | `/api/traffic/density` | Latest density for all lanes |
| `GET` | `/api/traffic/density/history` | Paginated density history |
| `POST` | `/api/traffic/video/process` | Upload + process a video file |

### Signals
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/signals/all` | All intersection signal states |
| `GET` | `/api/signals/{id}` | One intersection's state |
| `POST` | `/api/signals/{id}/manual` | Admin override signal timing |

### Emergency
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/emergency/activate` | Start a green corridor |
| `POST` | `/api/emergency/deactivate` | Clear a green corridor |
| `GET` | `/api/emergency/active` | List active emergencies |
| `POST` | `/api/emergency/simulate` | One-click test (demo) |

---

## 📡 MQTT Topics

| Topic | Direction | Payload |
|---|---|---|
| `traffic/signals/{id}/command` | Backend → Hardware | `{"command": "SET_TIMING", "lane_a_green": 35, ...}` |
| `traffic/signals/{id}/restore` | Backend → Hardware | `{"command": "RESTORE_NORMAL"}` |
| `traffic/emergency/alert` | Backend → Dashboard | Full `EmergencyEvent` JSON |
| `traffic/emergency/clear` | Backend → Dashboard | `event_id` string |
| `traffic/density/{id}` | ML → Backend | `{"lane_a_count": 12, ...}` |

---

## 🧠 ML Pipeline

```bash
# Run directly (without the backend running):
python ml/video_processor.py --video ml/test_videos/sample.mp4

# With API posting (backend must be running):
python ml/video_processor.py --video ml/test_videos/sample.mp4 --post-api

# Headless (no GUI window):
python ml/video_processor.py --video ... --no-display
```

Output: `sample_annotated.mp4` saved alongside the input file.

---

## 🔧 Signal Optimization Algorithm

```
total_density = lane_a_density + lane_b_density
if total_density == 0:
    lane_a_green = lane_b_green = 30s
else:
    lane_a_green = clamp(10s, 50s, (lane_a_density / total_density) × 60s)
    lane_b_green = 60s - lane_a_green
```

Density levels and colours:

| Density | Level | Color |
|---|---|---|
| 0–30% | LOW | 🟢 Green |
| 31–60% | MEDIUM | 🟡 Yellow |
| 61–80% | HIGH | 🟠 Orange |
| 81–100% | CRITICAL | 🔴 Red |

---

## 🗂️ Project Structure

```
smart-traffic-system/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point + WebSocket /ws
│   │   ├── config.py               # Pydantic settings
│   │   ├── models/
│   │   │   ├── database.py         # SQLAlchemy ORM (TimescaleDB-ready)
│   │   │   └── schemas.py          # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── traffic.py          # Density + video upload endpoints
│   │   │   ├── signals.py          # Signal state + manual override
│   │   │   └── emergency.py        # Green corridor management
│   │   ├── services/
│   │   │   ├── detector.py         # YOLOv8 vehicle detection
│   │   │   ├── density.py          # Rolling-average density calculator
│   │   │   ├── optimizer.py        # Adaptive signal timing
│   │   │   ├── corridor.py         # Emergency green corridor
│   │   │   └── pipeline.py         # End-to-end orchestrator
│   │   └── core/
│   │       ├── redis_client.py     # Async Redis wrapper
│   │       ├── mqtt_client.py      # Paho MQTT singleton
│   │       └── websocket_manager.py# WebSocket connection pool
│   ├── migrations/                 # Alembic migration scripts
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Navbar + sidebar layout
│   │   ├── components/
│   │   │   ├── Dashboard.jsx       # Main grid (signals, density, chart)
│   │   │   ├── SignalStatus.jsx    # SVG traffic light component
│   │   │   ├── EmergencyAlert.jsx  # Red banner + clear button
│   │   │   ├── IntersectionMap.jsx # Leaflet map
│   │   │   └── DensityChart.jsx    # Recharts line chart
│   │   ├── hooks/useWebSocket.js   # WS hook with auto-reconnect
│   │   └── api/trafficApi.js       # Axios API client
│   └── package.json
├── ml/
│   ├── video_processor.py          # Standalone CLI detector
│   ├── lane_detector.py            # Lane zone definitions
│   └── test_videos/                # Drop .mp4 files here
├── mosquitto/config/mosquitto.conf # MQTT broker config
├── demo.py                         # End-to-end demo script
├── docker-compose.yml
└── .env.example
```
